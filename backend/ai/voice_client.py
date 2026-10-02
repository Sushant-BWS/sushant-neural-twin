"""Client for the local Neural Twin Turbo voice service."""

from html import unescape
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json
import re
from uuid import uuid4
import wave


class VoiceServiceError(RuntimeError):
    """Raised when the local Turbo voice service cannot generate audio."""


def prepare_voice_text(text: str) -> str:
    """
    Clean presentation-only markup while preserving the complete answer.

    IMPORTANT:
    This function intentionally does NOT truncate the text.
    Long-text chunking is handled by the Turbo voice service.
    """

    clean_text = unescape(text.strip())

    # Convert Markdown links to their visible text.
    clean_text = re.sub(
        r"!?\[([^\]]*)\]\([^)]*\)",
        r"\1",
        clean_text,
    )

    # Remove URLs.
    clean_text = re.sub(
        r"https?://\S+|www\.\S+",
        "",
        clean_text,
        flags=re.IGNORECASE,
    )

    # Remove Markdown headings and bullet markers.
    clean_text = re.sub(
        r"^\s{0,3}#{1,6}\s*|^\s*[-*+]\s+",
        "",
        clean_text,
        flags=re.MULTILINE,
    )

    # Remove inline code markers.
    clean_text = re.sub(
        r"`([^`]*)`",
        r"\1",
        clean_text,
    )

    # Remove common Markdown emphasis markers.
    clean_text = (
        clean_text
        .replace("**", "")
        .replace("__", "")
        .replace("*", "")
        .replace("_", "")
    )

    # Replace ellipsis with a normal sentence pause.
    clean_text = clean_text.replace(
        "\u2026",
        ".",
    )

    # Normalize whitespace.
    clean_text = " ".join(
        clean_text.split()
    )

    # IMPORTANT:
    # Never truncate the answer here.
    return clean_text


def validate_wav(audio_bytes: bytes) -> None:
    """
    Reject empty, truncated, or unsupported audio before saving it.
    """

    if not audio_bytes:
        raise VoiceServiceError(
            "Turbo voice service returned empty audio."
        )

    try:
        with wave.open(
            BytesIO(audio_bytes),
            "rb",
        ) as audio:

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
                or sample_width not in (1, 2, 3, 4)
                or audio.getcomptype() != "NONE"
                or len(frame_bytes)
                != frames * channels * sample_width
            ):
                raise VoiceServiceError(
                    "Turbo voice service returned "
                    "an invalid PCM WAV."
                )

    except (
        wave.Error,
        EOFError,
        OSError,
    ) as exc:

        raise VoiceServiceError(
            "Turbo voice service returned "
            "an invalid PCM WAV."
        ) from exc


class VoiceClient:
    """Call the local Chatterbox Turbo voice service."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8002",
        output_directory: str | Path = "data/voice/generated",
        timeout: int = 600,
    ) -> None:

        self.base_url = base_url.rstrip("/")

        self.output_directory = Path(
            output_directory
        )

        self.timeout = timeout

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def health(self) -> bool:
        """Check whether the local Turbo voice service is available."""

        try:

            with urlopen(
                f"{self.base_url}/health",
                timeout=10,
            ) as response:

                return response.status == 200

        except (
            HTTPError,
            URLError,
            TimeoutError,
        ):

            return False

    def synthesize(
        self,
        text: str,
        language: str | None = None,
    ) -> str:
        """
        Generate a complete WAV file using Chatterbox Turbo.

        The complete cleaned answer is sent to the voice service.
        Long-text chunking is handled by voice_service_turbo.py.
        """

        clean_text = prepare_voice_text(text)

        if not clean_text:
            raise VoiceServiceError(
                "Cannot synthesize empty text."
            )

        # IMPORTANT:
        #
        # Chatterbox Turbo's endpoint accepts only:
        #
        # {
        #     "text": "..."
        # }
        #
        # Do NOT send language.
        #
        # Also do NOT truncate the text here.
        payload = json.dumps(
            {
                "text": clean_text,
            },
            ensure_ascii=False,
        ).encode("utf-8")

        request = Request(
            f"{self.base_url}/tts",
            data=payload,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "audio/wav",
            },
            method="POST",
        )

        try:

            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:

                content_type = (
                    response.headers.get_content_type()
                )

                if content_type not in {
                    "audio/wav",
                    "audio/wave",
                    "audio/x-wav",
                }:

                    raise VoiceServiceError(
                        "Turbo voice service returned "
                        f"unexpected content type: "
                        f"{content_type}."
                    )

                audio_bytes = response.read()

        except HTTPError as exc:

            detail = exc.read().decode(
                "utf-8",
                errors="replace",
            )

            raise VoiceServiceError(
                "Turbo voice service returned "
                f"HTTP {exc.code}: {detail}"
            ) from exc

        except (
            URLError,
            TimeoutError,
        ) as exc:

            raise VoiceServiceError(
                "Turbo voice service is unavailable. "
                "Make sure port 8002 is running."
            ) from exc

        validate_wav(audio_bytes)

        filename = (
            f"{uuid4().hex}.wav"
        )

        output_path = (
            self.output_directory
            / filename
        )

        try:

            output_path.write_bytes(
                audio_bytes
            )

        except OSError as exc:

            output_path.unlink(
                missing_ok=True
            )

            raise VoiceServiceError(
                "Could not save generated WAV audio: "
                f"{exc}"
            ) from exc

        return filename