from pathlib import Path
from threading import Lock
from uuid import uuid4

import torch
import torchaudio
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


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


# ---------------------------------------------------------
# DEVICE
# ---------------------------------------------------------

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Voice service device: {DEVICE}")


# ---------------------------------------------------------
# MODEL
# ---------------------------------------------------------

print("Loading Chatterbox Multilingual model...")

MODEL = ChatterboxMultilingualTTS.from_pretrained(
    device=DEVICE
)

print("Chatterbox Multilingual model loaded.")


# ---------------------------------------------------------
# PREPARE / CACHE SUSHANT VOICE
# ---------------------------------------------------------

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
            f"WARNING: Could not cache reference voice: {exc}"
        )

else:
    print(
        "WARNING: Sushant reference audio not found."
    )


# ---------------------------------------------------------
# FASTAPI
# ---------------------------------------------------------

app = FastAPI(
    title="Sushant Neural Twin Voice Service",
    version="1.1.0",
)


# ---------------------------------------------------------
# GENERATION LOCK
# ---------------------------------------------------------

generation_lock = Lock()


# ---------------------------------------------------------
# REQUEST MODEL
# ---------------------------------------------------------

class TTSRequest(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=300,
    )

    language: str = Field(
        default="en",
        pattern="^(en|hi)$",
    )


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "voice",
        "device": DEVICE,
        "reference_audio": REFERENCE_AUDIO.exists(),
        "reference_cached": REFERENCE_READY,
    }


# ---------------------------------------------------------
# TEXT CLEANUP
# ---------------------------------------------------------

def prepare_text(text: str) -> str:
    """
    Keep voice responses short and natural.
    """

    clean = " ".join(
        text.strip().split()
    )

    # Avoid unnecessarily long TTS generation.
    if len(clean) > 220:
        clean = clean[:220]

        # Try not to cut in the middle of a word.
        last_space = clean.rfind(" ")

        if last_space > 120:
            clean = clean[:last_space]

    return clean


# ---------------------------------------------------------
# LANGUAGE DETECTION
# ---------------------------------------------------------

def detect_language(text: str) -> str:
    """
    Devanagari -> Hindi.
    Everything else -> English.

    Roman Hinglish is intentionally routed to English
    because the English speech model handles Latin text
    more naturally than sending Roman Hindi to the Hindi
    tokenizer.
    """

    if any(
        "\u0900" <= char <= "\u097F"
        for char in text
    ):
        return "hi"

    return "en"


# ---------------------------------------------------------
# TTS
# ---------------------------------------------------------

@app.post("/tts")
def generate_voice(request: TTSRequest):

    if not REFERENCE_AUDIO.exists():
        raise HTTPException(
            status_code=500,
            detail="Reference voice file not found.",
        )

    text = prepare_text(request.text)

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Text is empty after cleanup.",
        )

    language = request.language

    output_file = (
        OUTPUT_DIR
        / f"{uuid4().hex}.wav"
    )

    try:

        with generation_lock:

            print(
                f"Generating voice | "
                f"language={language} | "
                f"text={text[:80]}"
            )

            # -------------------------------------------------
            # IMPORTANT:
            #
            # We DO NOT pass audio_prompt_path here.
            #
            # The Sushant voice conditionals were already
            # prepared once during startup.
            # -------------------------------------------------

            if REFERENCE_READY:

                wav = MODEL.generate(
                    text,
                    language_id=language,
                )

            else:

                # Safety fallback if reference preparation
                # failed during startup.
                wav = MODEL.generate(
                    text,
                    language_id=language,
                    audio_prompt_path=str(
                        REFERENCE_AUDIO
                    ),
                )

            torchaudio.save(
                str(output_file),
                wav,
                MODEL.sr,
            )

        print(
            f"Generated: {output_file.name}"
        )

        return FileResponse(
            path=output_file,
            media_type="audio/wav",
            filename="sushant_neural_twin.wav",
        )

    except Exception as exc:

        if output_file.exists():
            output_file.unlink()

        print(
            f"Voice generation failed: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"Voice generation failed: {exc}"
            ),
        ) from exc