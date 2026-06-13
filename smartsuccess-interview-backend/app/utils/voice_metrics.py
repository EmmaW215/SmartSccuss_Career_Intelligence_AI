"""
Phase 4 PR 4-3 — voice provider observability.

Records which provider actually served each STT/TTS call so we can measure the
$0-voice (GPU) success rate vs the paid OpenAI fallback. Emits a structlog
event per call (greppable: `voice.stt.provider` / `voice.tts.provider`) and
keeps an in-process counter exposed via /api/voice/status.

Pure + side-effect-light: a failed structlog import never breaks a voice call.
"""

from __future__ import annotations

import logging
import threading
from collections import Counter
from typing import Dict, Optional

try:
    import structlog

    _slog = structlog.get_logger("voice.metrics")
    _HAVE_STRUCTLOG = True
except Exception:  # pragma: no cover - structlog is a declared dep
    _slog = None
    _HAVE_STRUCTLOG = False

_stdlog = logging.getLogger("voice.metrics")

_lock = threading.Lock()
_counts: "Counter[str]" = Counter()

# Providers we expect per operation (for stable zero-rate denominators).
STT_PROVIDERS = ("gpu", "openai")
TTS_PROVIDERS = ("gpu", "edge_tts", "openai")


def record_provider(
    operation: str,
    provider: str,
    *,
    fallback: bool = False,
) -> None:
    """Count + log that `operation` ('stt'|'tts') was served by `provider`."""
    key = f"{operation}.{provider}"
    with _lock:
        _counts[key] += 1
        count = _counts[key]

    event = f"voice.{operation}.provider"
    if _HAVE_STRUCTLOG and _slog is not None:
        _slog.info(
            event,
            operation=operation,
            provider=provider,
            fallback=fallback,
            count=count,
        )
    else:  # pragma: no cover - fallback path
        _stdlog.info(
            "%s provider=%s fallback=%s count=%d",
            event, provider, fallback, count,
        )


def snapshot() -> Dict[str, int]:
    """Current per-(operation.provider) counts, e.g. {'stt.gpu': 12, ...}."""
    with _lock:
        return dict(_counts)


def _zero_cost_rate(operation: str, free_providers, paid_providers) -> Optional[float]:
    with _lock:
        free = sum(_counts.get(f"{operation}.{p}", 0) for p in free_providers)
        paid = sum(_counts.get(f"{operation}.{p}", 0) for p in paid_providers)
    total = free + paid
    return round(free / total, 4) if total else None


def stt_zero_cost_rate() -> Optional[float]:
    """Share of STT served free by the GPU (vs paid OpenAI). None if no calls."""
    return _zero_cost_rate("stt", ("gpu",), ("openai",))


def tts_zero_cost_rate() -> Optional[float]:
    """Share of TTS served free (GPU or Edge-TTS) vs paid OpenAI."""
    return _zero_cost_rate("tts", ("gpu", "edge_tts"), ("openai",))


def metrics_report() -> Dict[str, object]:
    """Compact report for /api/voice/status."""
    return {
        "counts": snapshot(),
        "stt_zero_cost_rate": stt_zero_cost_rate(),
        "tts_zero_cost_rate": tts_zero_cost_rate(),
    }


def reset() -> None:
    """Test helper: clear all counters."""
    with _lock:
        _counts.clear()
