"""
Regression tests for /api/voice/transcribe failure-path classification.

Background: empty / headers-only browser recordings (the "audio-capture" mic
failure) used to reach OpenAI, which rejects them with a 400 "Invalid file
format". The endpoint surfaced that as a misleading 500. These tests pin the
new behaviour:

  - sub-1KB uploads are short-circuited with a clean 422 (no OpenAI round-trip)
  - an OpenAI "Invalid file format" error maps to 422, not 500
  - a genuine transcription still returns 200 (working path unchanged)
"""

import pytest

from app.api.routes import voice as voice_route
from app.config import settings
from app.utils import voice_metrics


@pytest.fixture(autouse=True)
def _reset_metrics():
    voice_metrics.reset()
    yield
    voice_metrics.reset()


def _post(client, audio_bytes: bytes):
    return client.post(
        "/api/voice/transcribe",
        files={"audio": ("a.webm", audio_bytes, "audio/webm")},
        data={"language": "en"},
    )


class TestTranscribeGuard:
    def test_tiny_audio_returns_422_without_calling_openai(self, client, monkeypatch):
        # GPU off (default). Make the OpenAI path explode if it is ever reached.
        monkeypatch.setattr(voice_route, "GPU_AVAILABLE", False)

        def _boom(*a, **k):
            raise AssertionError("OpenAI must not be called for tiny audio")

        vs = voice_route.get_service()
        monkeypatch.setattr(vs, "transcribe", _boom)
        monkeypatch.setattr(vs, "is_available", lambda: True)

        resp = _post(client, b"\x1a\x45\xdf\xa3tiny-header")  # < 1KB
        assert resp.status_code == 422
        assert "record again" in resp.json()["detail"].lower() \
            or "audible" in resp.json()["detail"].lower()
        # No STT counted — we never reached a provider.
        assert voice_metrics.snapshot() == {}

    def test_openai_invalid_format_maps_to_422(self, client, monkeypatch):
        monkeypatch.setattr(voice_route, "GPU_AVAILABLE", False)

        async def _bad_format(audio_data, language):
            raise Exception(
                "Error code: 400 - {'error': {'message': \"Invalid file format. "
                "Supported formats: [...]\", 'type': 'invalid_request_error'}}"
            )

        vs = voice_route.get_service()
        monkeypatch.setattr(vs, "transcribe", _bad_format)
        monkeypatch.setattr(vs, "is_available", lambda: True)

        resp = _post(client, b"x" * 2048)  # passes the size guard, OpenAI rejects
        assert resp.status_code == 422
        assert "transcribed" in resp.json()["detail"].lower()

    def test_unexpected_error_still_500(self, client, monkeypatch):
        monkeypatch.setattr(voice_route, "GPU_AVAILABLE", False)

        async def _explode(audio_data, language):
            raise Exception("disk on fire")

        vs = voice_route.get_service()
        monkeypatch.setattr(vs, "transcribe", _explode)
        monkeypatch.setattr(vs, "is_available", lambda: True)

        resp = _post(client, b"x" * 2048)
        assert resp.status_code == 500

    def test_good_audio_still_returns_200(self, client, monkeypatch):
        monkeypatch.setattr(voice_route, "GPU_AVAILABLE", False)

        async def _ok(audio_data, language):
            return "hello world"

        vs = voice_route.get_service()
        monkeypatch.setattr(vs, "transcribe", _ok)
        monkeypatch.setattr(vs, "is_available", lambda: True)

        resp = _post(client, b"x" * 4096)
        assert resp.status_code == 200
        body = resp.json()
        assert body["text"] == "hello world"
        assert body["provider"] == "openai"
        assert voice_metrics.snapshot().get("stt.openai") == 1
