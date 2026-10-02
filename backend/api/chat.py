"""Chat API for the Sushant Neural Twin."""

from pathlib import Path
import json
import logging
import re
from threading import Lock
from time import perf_counter
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    HTTPException,
)
from fastapi.responses import FileResponse
from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from backend.ai.neural_twin import NeuralTwin
from backend.ai.voice_client import VoiceServiceError


router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)

twin = NeuralTwin()
logger = logging.getLogger(__name__)


# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================

class ChatRequest(BaseModel):
    """Incoming chat request."""

    message: str = Field(
        min_length=1
    )

    @field_validator("message")
    @classmethod
    def validate_message(
        cls,
        value: str,
    ) -> str:
        message = value.strip()

        if not message:
            raise ValueError(
                "message must not be empty"
            )

        return message


class ChatResponse(BaseModel):
    """Chat response returned to frontend."""

    answer: str

    safe: bool

    reasoning_summary: str

    evidence_count: int

    verifications: list[dict]

    # --------------------------------------------------------
    # Background voice job
    # --------------------------------------------------------

    voice_job_id: str | None = None

    voice_status: str = "not_started"

    # --------------------------------------------------------
    # Compatibility fields
    # --------------------------------------------------------

    audio_file: str | None = None

    voice_error: str | None = None


class VoiceStatusResponse(BaseModel):
    """Background voice job status."""

    job_id: str

    voice_job_id: str

    status: str

    audio_file: str | None = None

    voice_error: str | None = None


# ============================================================
# VOICE JOB STORAGE
# ============================================================

voice_jobs: dict[
    str,
    dict[str, object],
] = {}

voice_jobs_lock = Lock()


def _public_verifications(
    verifications: list[dict],
    reasoning_summary: str,
) -> list[dict]:
    """Return verification metadata without raw document excerpts."""

    public_verifications: list[dict] = []
    intent_match = re.search(
        r"for\s+([a-z]+)\s+intent",
        reasoning_summary,
        re.IGNORECASE,
    )
    intent = intent_match.group(1).lower() if intent_match else "profile"

    for verification in verifications:
        evidence_items = verification.get("evidence", [])
        public_evidence = []

        for evidence in evidence_items:
            if not isinstance(evidence, dict):
                continue

            source = str(evidence.get("source", "")).replace("\\", "/")
            title, summary = _summarize_evidence_source(
                source,
                str(evidence.get("content", "")),
                intent,
            )
            public_evidence.append(
                {
                    "source": source,
                    "title": title,
                    "summary": summary,
                    "evidence_type": evidence.get("evidence_type", ""),
                    "confidence": evidence.get("confidence"),
                }
            )

        public_verifications.append(
            {
                "claim": verification.get("claim", ""),
                "status": verification.get("status", "UNKNOWN"),
                "evidence": public_evidence,
                "overlap": verification.get("overlap", 0.0),
                "rationale": verification.get("rationale", ""),
            }
        )

    return public_verifications


def _summarize_evidence_source(
    source: str,
    content: str,
    intent: str,
) -> tuple[str, str]:
    """Create a small source-oriented summary, never a document excerpt."""

    filename = Path(source).name.lower()

    if filename == "education.json":
        try:
            record = json.loads(content)
        except (TypeError, json.JSONDecodeError):
            record = {}

        years = (
            f"{record['start_year']}-{record['end_year']}"
            if record.get("start_year") and record.get("end_year")
            else ""
        )
        summary = " · ".join(
            str(value).strip()
            for value in (
                record.get("degree"),
                record.get("institution"),
                record.get("location"),
                years,
            )
            if value
        )
        return "Education record", summary or "Degree, institution, and study period"

    if filename == "sushant_resume.pdf":
        summaries = {
            "education": "Education section and academic achievements",
            "project": "Documented project details",
            "skill": "Documented technical skills",
            "experience": "Documented work experience",
            "certification": "Documented certifications",
            "profile": "Documented profile details",
        }
        return "Resume", summaries.get(intent, "Supporting resume details")

    titles = {
        "projects.json": "Project record",
        "skills.json": "Skills record",
        "experience.json": "Experience record",
        "certifications.json": "Certification record",
        "profile.json": "Profile record",
    }
    summaries = {
        "project": "Documented project details",
        "skill": "Documented skills",
        "experience": "Documented experience",
        "certification": "Documented credentials",
        "thought": "Documented thought",
        "profile": "Documented profile details",
    }
    return (
        titles.get(filename, "Documented record"),
        summaries.get(intent, "Source-backed supporting details"),
    )


# ============================================================
# BACKGROUND VOICE WORKER
# ============================================================

def generate_voice_background(
    job_id: str,
    text: str,
) -> None:
    """
    Generate cloned voice in the background.

    The HTTP chat response is already returned before
    this function completes.
    """

    # --------------------------------------------------------
    # Processing
    # --------------------------------------------------------

    processing_started = perf_counter()

    with voice_jobs_lock:
        job = voice_jobs.setdefault(job_id, {})
        queued_at = job.get("queued_at", processing_started)
        text_response_seconds = job.get("text_response_seconds", 0.0)
        job.update({
            "status": "processing",
            "audio_file": None,
            "voice_error": None,
            "processing_started": processing_started,
        })

    print(
        f"[VOICE] Processing job: {job_id}"
    )

    try:

        # ----------------------------------------------------
        # Generate voice
        # ----------------------------------------------------

        audio_file = (
            twin.voice_client.synthesize(
                text
            )
        )

        # ----------------------------------------------------
        # Mark ready
        # ----------------------------------------------------

        generation_finished = perf_counter()

        with voice_jobs_lock:
            job = voice_jobs[job_id]
            job.update({
                "status": "ready",
                "audio_file": audio_file,
                "voice_error": None,
                "generation_seconds": generation_finished - processing_started,
                "total_voice_latency_seconds": generation_finished - queued_at,
            })

        logger.info(
            "voice job ready id=%s text_response_seconds=%.3f "
            "queue_seconds=%.3f generation_seconds=%.3f total_seconds=%.3f",
            job_id,
            text_response_seconds,
            processing_started - queued_at,
            generation_finished - processing_started,
            generation_finished - queued_at,
        )

        print(
            f"[VOICE] Ready: {job_id} "
            f"-> {audio_file}"
        )

    except VoiceServiceError as exc:

        failed_at = perf_counter()

        with voice_jobs_lock:
            job = voice_jobs[job_id]
            job.update({
                "status": "error",
                "audio_file": None,
                "voice_error": str(exc),
                "generation_seconds": failed_at - processing_started,
                "total_voice_latency_seconds": failed_at - queued_at,
            })

        logger.warning(
            "voice job failed id=%s text_response_seconds=%.3f "
            "queue_seconds=%.3f generation_seconds=%.3f total_seconds=%.3f error=%s",
            job_id,
            text_response_seconds,
            processing_started - queued_at,
            failed_at - processing_started,
            failed_at - queued_at,
            exc,
        )

        print(
            f"[VOICE] Failed: {job_id} "
            f"-> {exc}"
        )

    except Exception as exc:

        failed_at = perf_counter()

        with voice_jobs_lock:
            job = voice_jobs[job_id]
            job.update({
                "status": "error",
                "audio_file": None,
                "voice_error": (
                    f"Unexpected voice error: {exc}"
                ),
                "generation_seconds": failed_at - processing_started,
                "total_voice_latency_seconds": failed_at - queued_at,
            })

        logger.exception(
            "voice job failed unexpectedly id=%s text_response_seconds=%.3f "
            "queue_seconds=%.3f generation_seconds=%.3f total_seconds=%.3f",
            job_id,
            text_response_seconds,
            processing_started - queued_at,
            failed_at - processing_started,
            failed_at - queued_at,
        )

        print(
            f"[VOICE] Unexpected failure: "
            f"{job_id} -> {exc}"
        )


# ============================================================
# CHAT
# ============================================================

@router.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
) -> ChatResponse:
    """
    Return grounded text immediately.

    Voice generation happens in the background.
    """

    # --------------------------------------------------------
    # TEXT ONLY
    # --------------------------------------------------------
    #
    # This is the key performance change.
    #
    # NeuralTwin will NOT wait for Chatterbox.
    # --------------------------------------------------------

    request_started = perf_counter()

    result = twin.ask(
        request.message,
        generate_voice=False,
    )

    text_response_seconds = perf_counter() - request_started

    voice_job_id = None

    voice_status = "not_started"

    # --------------------------------------------------------
    # BACKGROUND VOICE
    # --------------------------------------------------------

    if (
        result["safe"]
        and result["answer"]
    ):

        voice_job_id = uuid4().hex

        voice_status = "queued"

        # ----------------------------------------------------
        # Register job
        # ----------------------------------------------------

        with voice_jobs_lock:

            voice_jobs[voice_job_id] = {
                "status": "queued",
                "audio_file": None,
                "voice_error": None,
                "queued_at": perf_counter(),
                "text_response_seconds": text_response_seconds,
            }

        # ----------------------------------------------------
        # Schedule voice generation
        # ----------------------------------------------------

        background_tasks.add_task(
            generate_voice_background,
            voice_job_id,
            result["answer"],
        )

    # --------------------------------------------------------
    # RETURN IMMEDIATELY
    # --------------------------------------------------------

    return ChatResponse(

        answer=result["answer"],

        safe=result["safe"],

        reasoning_summary=(
            result["reasoning_summary"]
        ),

        evidence_count=(
            result["evidence_count"]
        ),

        verifications=(
            _public_verifications(
                result["verifications"],
                result["reasoning_summary"],
            )
        ),

        voice_job_id=voice_job_id,

        voice_status=voice_status,

        audio_file=None,

        voice_error=None,
    )


# ============================================================
# VOICE STATUS
# ============================================================

@router.get(
    "/voice-status/{job_id}",
    response_model=VoiceStatusResponse,
)
def get_voice_status(
    job_id: str,
) -> VoiceStatusResponse:
    """
    Check background voice generation status.
    """

    # --------------------------------------------------------
    # Validate job ID
    # --------------------------------------------------------

    if (
        not job_id
        or Path(job_id).name != job_id
        or "/" in job_id
        or "\\" in job_id
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid voice job ID.",
        )

    # --------------------------------------------------------
    # Find job
    # --------------------------------------------------------

    with voice_jobs_lock:

        job = voice_jobs.get(
            job_id
        )

    if job is None:

        raise HTTPException(
            status_code=404,
            detail="Voice job not found.",
        )

    # --------------------------------------------------------
    # Return status
    # --------------------------------------------------------

    return VoiceStatusResponse(

        job_id=job_id,

        voice_job_id=job_id,

        status=(
            job.get("status")
            or "unknown"
        ),

        audio_file=(
            job.get("audio_file")
        ),

        voice_error=(
            job.get("voice_error")
        ),
    )


# ============================================================
# AUDIO
# ============================================================

AUDIO_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "voice"
    / "generated"
)


@router.get(
    "/audio/{filename}"
)
def get_chat_audio(
    filename: str,
):
    """Serve generated Neural Twin WAV audio."""

    # --------------------------------------------------------
    # Security validation
    # --------------------------------------------------------

    if (
        Path(filename).name != filename
        or "/" in filename
        or "\\" in filename
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid audio filename.",
        )

    if not filename.lower().endswith(
        ".wav"
    ):

        raise HTTPException(
            status_code=400,
            detail="Only WAV audio is supported.",
        )

    # --------------------------------------------------------
    # Resolve audio path
    # --------------------------------------------------------

    audio_path = (
        AUDIO_DIRECTORY
        / filename
    )

    # --------------------------------------------------------
    # Check file
    # --------------------------------------------------------

    if not audio_path.is_file():

        raise HTTPException(
            status_code=404,
            detail="Audio file not found.",
        )

    # --------------------------------------------------------
    # Return audio
    # --------------------------------------------------------

    return FileResponse(

        path=audio_path,

        media_type="audio/wav",

        filename=filename,
    )