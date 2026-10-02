import time
import torch
import torchaudio

from pathlib import Path
from chatterbox.tts_turbo import ChatterboxTurboTTS


BASE_DIR = Path(__file__).resolve().parent

REFERENCE_AUDIO = (
    BASE_DIR
    / "data"
    / "voice"
    / "sushant_reference.wav"
)

OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "voice"
    / "generated"
    / "nano_test.wav"
)


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print("=" * 60)
print("SUSHANT NEURAL TWIN - CHATTERBOX NANO TEST")
print("=" * 60)

print("Device:", DEVICE)
print("Reference:", REFERENCE_AUDIO)

print("\nLoading Nano...")

model = ChatterboxTurboTTS.from_pretrained(
    device=DEVICE,
    nano=True,
)

print("Nano loaded.")

text = (
    "Hi, I am Sushant. "
    "I enjoy learning cloud technologies, "
    "building practical projects, and automating repetitive work."
)

print("\nGenerating...")
print(text)

start = time.perf_counter()

wav = model.generate(
    text,
    audio_prompt_path=str(
        REFERENCE_AUDIO
    ),
)

elapsed = time.perf_counter() - start

torchaudio.save(
    str(OUTPUT_FILE),
    wav,
    model.sr,
)

print("\nGeneration completed.")
print(f"Time: {elapsed:.2f} seconds")
print("Output:", OUTPUT_FILE)
print("Sample rate:", model.sr)