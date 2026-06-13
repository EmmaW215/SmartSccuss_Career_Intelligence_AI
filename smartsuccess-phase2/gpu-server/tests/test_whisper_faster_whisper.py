"""
Phase 4 PR 4-1 tests — faster-whisper swap.

Two layers:
1. Contract tests (no GPU, no faster-whisper needed): a fake model mimicking
   faster-whisper's (segments_generator, info) return proves WhisperService
   still emits the exact {text, language, segments, confidence} shape that
   main.py and gpu_client.py depend on — i.e. the API schema is unchanged.
2. @pytest.mark.gpu WER sanity: real faster-whisper transcription on fixture
   WAVs, optionally compared to the OpenAI Whisper API. Run on the GPU host:
       RUN_GPU_TESTS=1 pytest -m gpu tests/test_whisper_faster_whisper.py
"""

import importlib.util
import os
from pathlib import Path

import pytest

# Load whisper_service directly by file path: importing it via the `services`
# package would execute services/__init__.py, which imports tts_service ->
# torch (absent in the contract-test env). The module under test itself only
# needs torch/faster-whisper lazily, so this loads cleanly without them.
_WS_PATH = Path(__file__).resolve().parents[1] / "services" / "whisper_service.py"
_spec = importlib.util.spec_from_file_location("whisper_service_under_test", _WS_PATH)
_ws_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ws_module)
WhisperService = _ws_module.WhisperService

FIXTURES = Path(__file__).parent / "fixtures"


# ──────────────────────────────────────────────────────────────────
# Fakes mimicking faster-whisper's API surface (no torch / no model)
# ──────────────────────────────────────────────────────────────────

class _FakeSegment:
    def __init__(self, text, start, end, avg_logprob):
        self.text = text
        self.start = start
        self.end = end
        self.avg_logprob = avg_logprob


class _FakeInfo:
    def __init__(self, language):
        self.language = language
        self.language_probability = 0.99


class _FakeModel:
    """Mimics faster_whisper.WhisperModel.transcribe -> (gen, info)."""

    def __init__(self, segments, language="en"):
        self._segments = segments
        self._language = language
        self.last_kwargs = None

    def transcribe(self, audio_path, **kwargs):
        self.last_kwargs = kwargs
        return iter(self._segments), _FakeInfo(self._language)


def _service_with_fake(segments, language="en"):
    # __init__ tries to load faster-whisper (absent here) -> model=None,
    # which is fine; we inject the fake model directly.
    service = WhisperService.__new__(WhisperService)
    service.device = "cpu"
    service.model_size = "large-v3"
    service.compute_type = "int8"
    service.model = _FakeModel(segments, language)
    return service


class TestTranscribeContractUnchanged:
    def test_returns_exact_schema_keys(self):
        service = _service_with_fake(
            [
                _FakeSegment(" Hello there.", 0.0, 1.2, -0.15),
                _FakeSegment(" How are you?", 1.2, 2.5, -0.25),
            ]
        )
        result = service._transcribe_sync("/tmp/fake.webm", None)

        # Exact keys main.py reads: result["text"], result["language"],
        # result.get("confidence"), result.get("segments")
        assert set(result.keys()) == {"text", "language", "segments", "confidence"}
        assert result["text"] == "Hello there. How are you?"
        assert result["language"] == "en"
        assert isinstance(result["segments"], list)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_segment_dict_shape_preserved(self):
        service = _service_with_fake([_FakeSegment(" Test.", 0.0, 0.5, -0.1)])
        seg = service._transcribe_sync("/tmp/fake.webm", None)["segments"][0]
        assert set(seg.keys()) == {"start", "end", "text", "avg_logprob"}

    def test_confidence_from_avg_logprob(self):
        # avg_logprob 0.0 -> confidence 1.0; -1.0 -> 0.0 (existing formula)
        service = _service_with_fake([_FakeSegment(" x", 0.0, 1.0, 0.0)])
        assert service._transcribe_sync("/tmp/f.webm", None)["confidence"] == 1.0
        service2 = _service_with_fake([_FakeSegment(" x", 0.0, 1.0, -1.0)])
        assert service2._transcribe_sync("/tmp/f.webm", None)["confidence"] == 0.0

    def test_empty_segments_default_confidence(self):
        service = _service_with_fake([], language="es")
        result = service._transcribe_sync("/tmp/f.webm", None)
        assert result["text"] == ""
        assert result["language"] == "es"
        assert result["confidence"] == 0.9  # _calculate_confidence default

    def test_vad_filter_and_language_passed_through(self):
        service = _service_with_fake([_FakeSegment(" hi", 0.0, 0.3, -0.1)])
        service._transcribe_sync("/tmp/f.webm", "zh")
        assert service.model.last_kwargs["vad_filter"] is True
        assert service.model.last_kwargs["task"] == "transcribe"
        assert service.model.last_kwargs["language"] == "zh"

    @pytest.mark.asyncio
    async def test_transcribe_async_wrapper_returns_same_shape(self):
        service = _service_with_fake([_FakeSegment(" Async ok.", 0.0, 1.0, -0.1)])
        result = await service.transcribe(b"fake-audio-bytes", language=None)
        assert result["text"] == "Async ok."
        assert set(result.keys()) == {"text", "language", "segments", "confidence"}

    @pytest.mark.asyncio
    async def test_transcribe_raises_when_model_unloaded(self):
        service = WhisperService.__new__(WhisperService)
        service.model = None
        with pytest.raises(Exception):
            await service.transcribe(b"data", None)


# ──────────────────────────────────────────────────────────────────
# Real GPU WER sanity — manual, on the GPU host
# ──────────────────────────────────────────────────────────────────

def _wer(reference: str, hypothesis: str) -> float:
    """Word error rate via Levenshtein distance over word tokens."""
    ref = reference.lower().split()
    hyp = hypothesis.lower().split()
    if not ref:
        return 0.0 if not hyp else 1.0
    # DP edit distance
    dp = list(range(len(hyp) + 1))
    for i in range(1, len(ref) + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, len(hyp) + 1):
            cur = dp[j]
            dp[j] = min(
                dp[j] + 1,
                dp[j - 1] + 1,
                prev + (ref[i - 1] != hyp[j - 1]),
            )
            prev = cur
    return dp[len(hyp)] / len(ref)


@pytest.mark.gpu
@pytest.mark.skipif(
    not os.getenv("RUN_GPU_TESTS"),
    reason="set RUN_GPU_TESTS=1 on the GPU host to run real faster-whisper WER tests",
)
@pytest.mark.asyncio
async def test_faster_whisper_wer_on_fixtures():
    """Transcribe 5 fixture WAVs; assert WER is sane.

    Drop WAVs in tests/fixtures/ named <name>.wav with a sibling <name>.txt
    reference transcript. Accented-English samples recommended (PRD).
    """
    wavs = sorted(FIXTURES.glob("*.wav"))
    if not wavs:
        pytest.skip("no fixture WAVs in tests/fixtures/")

    service = WhisperService()
    assert service.model is not None, "faster-whisper failed to load on the GPU host"

    for wav in wavs:
        ref_file = wav.with_suffix(".txt")
        audio = wav.read_bytes()
        result = await service.transcribe(audio, language="en")
        assert result["text"], f"empty transcription for {wav.name}"
        assert set(result.keys()) == {"text", "language", "segments", "confidence"}

        if ref_file.exists():
            wer = _wer(ref_file.read_text(), result["text"])
            assert wer <= 0.25, f"{wav.name}: WER {wer:.2f} exceeds 0.25 sanity bound"
