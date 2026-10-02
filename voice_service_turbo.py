from pathlib import Path
from threading import Lock
from uuid import uuid4
import re
import wave

import torch
import torchaudio
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from chatterbox.tts_turbo import ChatterboxTurboTTS


# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

REFERENCE_AUDIO = (
    BASE_DIR
    / "data"
    / "voice"
    / "sushant_reference.wav"
)

OUTPUT_DIR = (
    BASE_DIR
    / "data"
    / "voice"
    / "generated"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# Device
# --------------------------------------------------

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print("=" * 60)
print("Sushant Neural Twin - Turbo Voice Service")
print(f"Device: {DEVICE}")
print("=" * 60)


# --------------------------------------------------
# Load Turbo model
# --------------------------------------------------

print("Loading Chatterbox Turbo model...")

MODEL = ChatterboxTurboTTS.from_pretrained(
    device=DEVICE
)

print("Chatterbox Turbo model loaded.")


# --------------------------------------------------
# Prepare reference voice once
# --------------------------------------------------

REFERENCE_READY = False

if REFERENCE_AUDIO.exists():
    try:
        print("Preparing Sushant reference voice...")

        MODEL.prepare_conditionals(
            str(REFERENCE_AUDIO)
        )

        REFERENCE_READY = True

        print("Sushant reference voice cached.")

    except Exception as exc:
        print(
            f"Reference voice preparation failed: {exc}"
        )
else:
    print(
        "WARNING: Reference voice file not found."
    )


# --------------------------------------------------
# FastAPI
# --------------------------------------------------

app = FastAPI(
    title="Sushant Neural Twin Turbo Voice Service",
    version="1.1.0",
)


generation_lock = Lock()


# --------------------------------------------------
# Text chunking
# --------------------------------------------------

MAX_CHUNK_CHARS = 180

SENTENCE_PATTERN = re.compile(
    r"(?<=[.!?।])\s+"
)


def split_voice_text(text: str) -> list[str]:
    """
    Split long answers into natural sentence/word chunks.

    Important:
    We NEVER truncate the answer.
    Every part of the answer must be synthesized.
    """

    text = " ".join(text.strip().split())

    if not text:
        return []

    sentences = SENTENCE_PATTERN.split(text)

    chunks: list[str] = []
    current = ""

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        candidate = (
            f"{current} {sentence}".strip()
        )

        if (
            current
            and len(candidate) > MAX_CHUNK_CHARS
        ):
            chunks.append(current)
            current = sentence

        else:
            current = candidate

    if current:
        chunks.append(current)

    # Handle an unusually long single sentence.
    final_chunks: list[str] = []

    for chunk in chunks:

        if len(chunk) <= MAX_CHUNK_CHARS:
            final_chunks.append(chunk)
            continue

        words = chunk.split()
        current_word_chunk = ""

        for word in words:

            candidate = (
                f"{current_word_chunk} {word}"
            ).strip()

            if (
                current_word_chunk
                and len(candidate) > MAX_CHUNK_CHARS
            ):
                final_chunks.append(
                    current_word_chunk
                )

                current_word_chunk = word

            else:
                current_word_chunk = candidate

        if current_word_chunk:
            final_chunks.append(
                current_word_chunk
            )

    return final_chunks


# --------------------------------------------------
# WAV validation
# --------------------------------------------------

def validate_generated_wav(path: Path) -> None:
    """Ensure Chatterbox output is valid PCM WAV audio."""

    if (
        not path.is_file()
        or path.stat().st_size <= 44
    ):
        raise RuntimeError(
            "Generated WAV is missing or empty."
        )

    try:

        with wave.open(str(path), "rb") as audio:

            channels = audio.getnchannels()
            sample_rate = audio.getframerate()
            frames = audio.getnframes()
            sample_width = audio.getsampwidth()

            frame_bytes = audio.readframes(
                frames
            )

            if (
                channels not in (1, 2)
                or not 8000 <= sample_rate <= 192000
                or frames <= 0
                or sample_width != 2
                or audio.getcomptype() != "NONE"
                or len(frame_bytes)
                != frames * channels * sample_width
            ):
                raise RuntimeError(
                    "Generated WAV failed PCM validation."
                )

    except (
        wave.Error,
        EOFError,
        OSError,
    ) as exc:

        raise RuntimeError(
            "Generated WAV is not a valid PCM WAV file."
        ) from exc


# --------------------------------------------------
# Request model
# --------------------------------------------------

class TTSRequest(BaseModel):

    text: str = Field(
        min_length=1,
        max_length=10000,
    )


# --------------------------------------------------
# Health
# --------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "voice-turbo",
        "device": DEVICE,
        "reference_audio": REFERENCE_AUDIO.exists(),
        "reference_cached": REFERENCE_READY,
    }


# --------------------------------------------------
# Generate one chunk
# --------------------------------------------------

def generate_chunk(text: str) -> torch.Tensor:

    print(
        f"Generating voice chunk "
        f"({len(text)} chars): {text[:80]}"
    )

    if REFERENCE_READY:

        wav = MODEL.generate(
            text,
            temperature=0.7,
            top_p=0.9,
            top_k=500,
            repetition_penalty=1.15,
        )

    else:

        wav = MODEL.generate(
            text,
            audio_prompt_path=str(
                REFERENCE_AUDIO
            ),
            temperature=0.7,
            top_p=0.9,
            top_k=500,
            repetition_penalty=1.15,
        )

    if not isinstance(wav, torch.Tensor):
        raise RuntimeError(
            "Chatterbox returned an invalid audio tensor."
        )

    return wav.detach().cpu()


# --------------------------------------------------
# Combine audio chunks
# --------------------------------------------------

def combine_audio_chunks(
    chunks: list[torch.Tensor],
) -> torch.Tensor:

    if not chunks:
        raise RuntimeError(
            "No audio chunks were generated."
        )

    normalized: list[torch.Tensor] = []

    for chunk in chunks:

        if chunk.ndim == 1:
            chunk = chunk.unsqueeze(0)

        if chunk.ndim != 2:
            raise RuntimeError(
                "Invalid Chatterbox audio tensor shape."
            )

        normalized.append(chunk)

    channels = normalized[0].shape[0]

    fixed_chunks = []

    # Small natural pause between sentences.
    pause_seconds = 0.12

    pause_samples = int(
        MODEL.sr * pause_seconds
    )

    pause = torch.zeros(
        (
            channels,
            pause_samples,
        ),
        dtype=normalized[0].dtype,
    )

    for index, chunk in enumerate(normalized):

        if chunk.shape[0] != channels:
            raise RuntimeError(
                "Audio chunks have incompatible channel counts."
            )

        fixed_chunks.append(chunk)

        if index < len(normalized) - 1:
            fixed_chunks.append(pause)

    return torch.cat(
        fixed_chunks,
        dim=1,
    )


# --------------------------------------------------
# Generate complete voice
# --------------------------------------------------

@app.post("/tts")
def generate_voice(request: TTSRequest):

    text = " ".join(
        request.text.strip().split()
    )

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty.",
        )

    chunks = split_voice_text(text)

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No usable voice text found.",
        )

    print()
    print(
        f"Voice request received: "
        f"{len(text)} characters"
    )

    print(
        f"Voice chunks: {len(chunks)}"
    )

    output_file = (
        OUTPUT_DIR
        / f"{uuid4().hex}.wav"
    )

    try:

        with generation_lock:

            generated_chunks = []

            for index, chunk in enumerate(
                chunks,
                start=1,
            ):

                print(
                    f"Generating chunk "
                    f"{index}/{len(chunks)}"
                )

                generated_chunks.append(
                    generate_chunk(chunk)
                )

            final_wav = combine_audio_chunks(
                generated_chunks
            )

            torchaudio.save(
                str(output_file),
                final_wav,
                MODEL.sr,
                encoding="PCM_S",
                bits_per_sample=16,
            )

            validate_generated_wav(
                output_file
            )

        print(
            f"Generated complete Turbo voice: "
            f"{output_file.name}"
        )

        return FileResponse(
            path=output_file,
            media_type="audio/wav",
            filename=(
                "sushant_neural_twin_turbo.wav"
            ),
        )

    except Exception as exc:

        if output_file.exists():
            output_file.unlink()

        print(
            f"Turbo voice generation failed: "
            f"{exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Turbo voice generation failed: "
                f"{exc}"
            ),
        ) from exc


# --------------------------------------------------
# Run directly
# --------------------------------------------------

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8002,
    )