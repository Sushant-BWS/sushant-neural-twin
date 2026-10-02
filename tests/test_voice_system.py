"""Tests for the local Turbo voice pipeline."""

from email.message import Message
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import patch
from urllib.error import HTTPError
from uuid import uuid4

from backend.ai.voice_client import (
    VoiceClient,
    VoiceServiceError,
    prepare_voice_text,
)
from backend.api import chat as chat_api
from backend.main import app


def make_wav() -> bytes:
    buffer = BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b"\0\0" * 240)
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, body: bytes, content_type: str = "audio/wav") -> None:
        self.body = body
        self.status = 200
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class VoiceClientTests(unittest.TestCase):
    def test_health_checks_the_configured_turbo_service(self) -> None:
        client = VoiceClient()
        with patch(
            "backend.ai.voice_client.urlopen",
            return_value=FakeResponse(b""),
        ) as urlopen:
            self.assertTrue(client.health())

        request = urlopen.call_args.args[0]
        self.assertEqual(request, "http://127.0.0.1:8002/health")

    def test_prepares_voice_text_without_changing_wording(self) -> None:
        text = prepare_voice_text(
            "**Hello** [profile](https://example.com)\nworld."
        )

        self.assertEqual(text, "Hello profile world.")

    def test_voice_text_respects_turbo_limit_at_word_boundary(self) -> None:
        text = prepare_voice_text("word " * 100)

        self.assertLessEqual(len(text), 220)
        self.assertFalse(text.endswith(" "))

    def test_synthesize_sends_text_only_to_turbo_and_validates_wav(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = VoiceClient(output_directory=directory)
            with patch(
                "backend.ai.voice_client.urlopen",
                return_value=FakeResponse(make_wav()),
            ) as urlopen:
                filename = client.synthesize("  Hello   world.  ")

            request = urlopen.call_args.args[0]
            self.assertEqual(
                request.full_url,
                "http://127.0.0.1:8002/tts",
            )
            self.assertEqual(
                json.loads(request.data.decode("utf-8")),
                {"text": "Hello world."},
            )
            self.assertEqual(urlopen.call_args.kwargs["timeout"], 600)

            output = Path(directory) / filename
            with wave.open(str(output), "rb") as audio:
                self.assertGreater(audio.getnframes(), 0)
                self.assertEqual(audio.getframerate(), 24000)
                self.assertEqual(audio.getnchannels(), 1)
                self.assertEqual(audio.getsampwidth(), 2)

    def test_synthesize_rejects_invalid_audio_and_content_type(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = VoiceClient(output_directory=directory)
            responses = [
                FakeResponse(b"not a wav"),
                FakeResponse(make_wav(), "application/json"),
            ]

            for response in responses:
                with patch(
                    "backend.ai.voice_client.urlopen",
                    return_value=response,
                ):
                    with self.assertRaises(VoiceServiceError):
                        client.synthesize("Hello world.")

            self.assertEqual(list(Path(directory).glob("*.wav")), [])

    def test_synthesize_reports_http_and_timeout_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = VoiceClient(output_directory=directory)
            http_error = HTTPError(
                "http://127.0.0.1:8002/tts",
                503,
                "service unavailable",
                Message(),
                BytesIO(b"voice service busy"),
            )
            with patch(
                "backend.ai.voice_client.urlopen",
                side_effect=http_error,
            ):
                with self.assertRaisesRegex(VoiceServiceError, "HTTP 503"):
                    client.synthesize("Hello world.")

            with patch(
                "backend.ai.voice_client.urlopen",
                side_effect=TimeoutError("timed out"),
            ):
                with self.assertRaisesRegex(VoiceServiceError, "port 8002"):
                    client.synthesize("Hello world.")


class VoiceJobTests(unittest.TestCase):
    def setUp(self) -> None:
        with chat_api.voice_jobs_lock:
            chat_api.voice_jobs.clear()

    def tearDown(self) -> None:
        with chat_api.voice_jobs_lock:
            chat_api.voice_jobs.clear()

    def test_chat_returns_queued_job_without_running_voice_inline(self) -> None:
        background_tasks = BackgroundTasks()
        with patch.object(
            chat_api.twin,
            "ask",
            return_value={
                "answer": "Grounded answer.",
                "safe": True,
                "reasoning_summary": "Documented answer.",
                "evidence_count": 1,
                "verifications": [
                    {
                        "claim": "Grounded answer.",
                        "status": "VERIFIED",
                        "evidence": [
                            {
                                "source": "data/profile/profile.json",
                                "content": "RAW PRIVATE DOCUMENT TEXT",
                                "evidence_type": "RETRIEVED_DOCUMENT",
                                "confidence": 0.99,
                            }
                        ],
                        "overlap": 1.0,
                        "rationale": "Directly supported.",
                    }
                ],
            },
        ), patch.object(
            chat_api.twin.voice_client,
            "synthesize",
        ) as synthesize:
            response = chat_api.chat(
                chat_api.ChatRequest(message="Question?"),
                background_tasks,
            )

        self.assertEqual(response.voice_status, "queued")
        self.assertIsNotNone(response.voice_job_id)
        self.assertEqual(len(background_tasks.tasks), 1)
        synthesize.assert_not_called()
        self.assertEqual(
            response.verifications[0]["evidence"],
            [
                {
                    "source": "data/profile/profile.json",
                    "title": "Profile record",
                    "summary": "Documented profile details",
                    "evidence_type": "RETRIEVED_DOCUMENT",
                    "confidence": 0.99,
                }
            ],
        )
        self.assertNotIn(
            "RAW PRIVATE DOCUMENT TEXT",
            str(response.verifications),
        )
        self.assertEqual(
            background_tasks.tasks[0].args[1],
            "Grounded answer.",
        )
        self.assertEqual(
            chat_api.voice_jobs[response.voice_job_id]["status"],
            "queued",
        )

    def test_voice_job_transitions_from_processing_to_ready(self) -> None:
        job_id = uuid4().hex
        chat_api.voice_jobs[job_id] = {
            "status": "queued",
            "audio_file": None,
            "voice_error": None,
        }
        observed_status = []

        def synthesize(_text: str) -> str:
            observed_status.append(
                chat_api.get_voice_status(job_id).status
            )
            return "answer.wav"

        with patch.object(
            chat_api.twin.voice_client,
            "synthesize",
            side_effect=synthesize,
        ):
            chat_api.generate_voice_background(job_id, "Answer.")

        status = chat_api.get_voice_status(job_id)
        self.assertEqual(observed_status, ["processing"])
        self.assertEqual(status.status, "ready")
        self.assertEqual(status.audio_file, "answer.wav")
        self.assertEqual(status.job_id, job_id)
        self.assertEqual(status.voice_job_id, job_id)

        response = TestClient(app).get(
            f"/api/chat/voice-status/{job_id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["voice_job_id"], job_id)

    def test_voice_job_records_failure_instead_of_staying_processing(self) -> None:
        job_id = uuid4().hex
        chat_api.voice_jobs[job_id] = {
            "status": "queued",
            "audio_file": None,
            "voice_error": None,
        }
        with patch.object(
            chat_api.twin.voice_client,
            "synthesize",
            side_effect=VoiceServiceError("Service unavailable."),
        ):
            chat_api.generate_voice_background(job_id, "Answer.")

        status = chat_api.get_voice_status(job_id)
        self.assertEqual(status.status, "error")
        self.assertIsNone(status.audio_file)
        self.assertEqual(status.voice_error, "Service unavailable.")

    def test_audio_endpoint_serves_wav_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            audio_bytes = make_wav()
            filename = "answer.wav"
            (Path(directory) / filename).write_bytes(audio_bytes)
            with patch.object(chat_api, "AUDIO_DIRECTORY", Path(directory)):
                response = TestClient(app).get(
                    f"/api/chat/audio/{filename}"
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "audio/wav")
        self.assertEqual(response.content, audio_bytes)


class FrontendServingTests(unittest.TestCase):
    def test_fastapi_root_serves_existing_frontend_and_assets(self) -> None:
        client = TestClient(app)

        page = client.get("/")
        stylesheet = client.get("/frontend/styles/app.css")
        script = client.get("/frontend/components/app.js")

        self.assertEqual(page.status_code, 200)
        self.assertTrue(page.headers["content-type"].startswith("text/html"))
        self.assertIn(b"Sushant Neural Twin", page.content)
        self.assertEqual(stylesheet.status_code, 200)
        self.assertTrue(stylesheet.headers["content-type"].startswith("text/css"))
        self.assertEqual(script.status_code, 200)
        self.assertIn(b"/api/chat/chat", script.content)

        self.assertEqual(client.get("/docs").status_code, 200)
        self.assertEqual(client.get("/health").status_code, 200)


if __name__ == "__main__":
    unittest.main()