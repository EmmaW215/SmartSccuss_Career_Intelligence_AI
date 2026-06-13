"""
Phase 4 PR 4-3 — voice provider observability tests.

Covers the counter/rate logic and that the /transcribe + /synthesize endpoints
record the provider that actually served the call (gpu vs openai fallback).
"""

import io

import pytest

from app.api.routes import voice as voice_route
from app.config import settings
from app.utils import voice_metrics


@pytest.fixture(autouse=True)
def _reset_metrics():
    voice_metrics.reset()
    yield
    voice_metrics.reset()


# ──────────────────────────────────────────────────────────────────
# Counter / rate logic
# ──────────────────────────────────────────────────────────────────

class TestVoiceMetricsCore:
    def test_records_and_counts(self):
        voice_metrics.record_provider("stt", "gpu")
        voice_metrics.record_provider("stt", "gpu")
        voice_metrics.record_provider("stt", "openai", fallback=True)
        snap = voice_metrics.snapshot()
        assert snap["stt.gpu"] == 2
        assert snap["stt.openai"] == 1

    def test_stt_zero_cost_rate(self):
        assert voice_metrics.stt_zero_cost_rate() is None  # no calls yet
        voice_metrics.record_provider("stt", "gpu")
        voice_metrics.record_provider("stt", "gpu")
        voice_metrics.record_provider("stt", "gpu")
        voice_metrics.record_provider("stt", "openai", fallback=True)
        assert voice_metrics.stt_zero_cost_rate() == 0.75  # 3 gpu / 4 total

    def test_tts_zero_cost_rate_counts_edge_tts_as_free(self):
        voice_metrics.record_provider("tts", "gpu")
        voice_metrics.record_provider("tts", "edge_tts", fallback=True)
        voice_metrics.record_provider("tts", "openai", fallback=True)
        assert voice_metrics.tts_zero_cost_rate() == round(2 / 3, 4)

    def test_metrics_report_shape(self):
        voice_metrics.record_provider("stt", "gpu")
        report = voice_metrics.metrics_report()
        assert set(report) == {"counts", "stt_zero_cost_rate", "tts_zero_cost_rate"}
        assert report["counts"]["stt.gpu"] == 1


# ──────────────────────────────────────────────────────────────────
# Endpoint integration
# ──────────────────────────────────────────────────────────────────

class _FakeGpuClient:
    def __init__(self, transcript="gpu transcript"):
        self._transcript = transcript

    async def transcribe(self, audio_data, language):
        return self._transcript, voice_route.VoiceProvider.GPU


class _FailingGpuClient:
    async def transcribe(self, audio_data, language):
        raise Exception("GPU down")


class TestTranscribeEndpointRecordsProvider:
    def test_gpu_success_records_gpu(self, client, monkeypatch):
        monkeypatch.setattr(settings, "use_gpu_voice", True)
        monkeypatch.setattr(voice_route, "GPU_AVAILABLE", True)
        monkeypatch.setattr(voice_route, "get_gpu_client", lambda: _FakeGpuClient())

        resp = client.post(
            "/api/voice/transcribe",
            files={"audio": ("a.webm", b"x" * 2048, "audio/webm")},  # >1KB: passes the empty-audio guard
            data={"language": "en"},
        )
        assert resp.status_code == 200
        assert resp.json()["provider"] == "gpu"
        assert voice_metrics.snapshot().get("stt.gpu") == 1
        assert voice_metrics.stt_zero_cost_rate() == 1.0

    def test_gpu_failure_falls_back_and_records_openai(self, client, monkeypatch):
        monkeypatch.setattr(settings, "use_gpu_voice", True)
        monkeypatch.setattr(voice_route, "GPU_AVAILABLE", True)
        monkeypatch.setattr(voice_route, "get_gpu_client", lambda: _FailingGpuClient())

        async def _fake_openai_transcribe(audio_data, language):
            return "openai transcript"

        vs = voice_route.get_service()
        monkeypatch.setattr(vs, "transcribe", _fake_openai_transcribe)
        monkeypatch.setattr(vs, "is_available", lambda: True)

        resp = client.post(
            "/api/voice/transcribe",
            files={"audio": ("a.webm", b"x" * 2048, "audio/webm")},  # >1KB: passes the empty-audio guard
            data={"language": "en"},
        )
        assert resp.status_code == 200
        assert resp.json()["provider"] == "openai"
        snap = voice_metrics.snapshot()
        assert snap.get("stt.openai") == 1
        assert "stt.gpu" not in snap
        assert voice_metrics.stt_zero_cost_rate() == 0.0  # GPU attempted, fell back

    def test_status_endpoint_exposes_metrics(self, client, monkeypatch):
        monkeypatch.setattr(voice_route, "GPU_AVAILABLE", False)
        voice_metrics.record_provider("stt", "gpu")
        resp = client.get("/api/voice/status")
        assert resp.status_code == 200
        pm = resp.json()["provider_metrics"]
        assert pm["counts"]["stt.gpu"] == 1
        assert pm["stt_zero_cost_rate"] == 1.0
