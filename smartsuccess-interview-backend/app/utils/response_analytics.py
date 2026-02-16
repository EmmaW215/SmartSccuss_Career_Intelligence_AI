"""
Response Analytics & Anti-Gaming Heuristics
FIX: I-D3 (Sprint 5) — Basic detection of potentially gamed responses

IMPORTANT: These are heuristics only. Do NOT penalize users based on flags alone.
Use for analytics and pattern tracking.
"""

import logging
import statistics
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def detect_potential_gaming(response: str, response_time_seconds: float = 0) -> Dict[str, Any]:
    """
    Basic heuristics to flag potentially gamed (AI-generated/pasted) responses.
    
    Returns dict with flags and confidence level.
    NEVER use to penalize — only for analytics.
    """
    flags = []
    
    words = len(response.split())
    
    # Flag 1: Extremely fast, long response (likely paste)
    if response_time_seconds > 0 and words > 100 and response_time_seconds < 10:
        flags.append("rapid_long_response")
    
    # Flag 2: Overly formal/structured for a chat (AI-generated indicator)
    formal_markers = [
        "in conclusion", "furthermore", "it is worth noting",
        "in summary", "firstly", "secondly", "thirdly",
        "to summarize", "in addition", "moreover", "consequently"
    ]
    formal_count = sum(1 for m in formal_markers if m in response.lower())
    if formal_count >= 3:
        flags.append("overly_structured")
    
    # Flag 3: Perfect formatting (bullet points in chat)
    if response.count("\n- ") >= 3 or response.count("\n• ") >= 3:
        flags.append("formatted_response")
    
    # Flag 4: Extremely long response for an interview chat
    if words > 500:
        flags.append("unusually_long")
    
    return {
        "flags": flags,
        "is_suspicious": len(flags) >= 2,
        "confidence": "low",  # Heuristics only, never definitive
        "word_count": words
    }


def compute_score_summary(scores: List[float]) -> Dict[str, Any]:
    """
    FIX: I-D2 (Sprint 5) — Add score distribution metrics beyond simple averaging.
    
    Captures consistency, trend, and range — not just mean.
    """
    if not scores:
        return {
            "average": 0,
            "min_score": 0,
            "max_score": 0,
            "std_dev": 0,
            "consistency": "unknown",
            "trend": "unknown"
        }
    
    avg = statistics.mean(scores)
    std = statistics.stdev(scores) if len(scores) > 1 else 0
    
    return {
        "average": round(avg, 2),
        "min_score": min(scores),
        "max_score": max(scores),
        "std_dev": round(std, 2),
        "consistency": (
            "high" if std < 0.5 else
            "moderate" if std < 1.0 else
            "low"
        ),
        "trend": (
            "improving" if len(scores) >= 2 and scores[-1] > scores[0] else
            "declining" if len(scores) >= 2 and scores[-1] < scores[0] else
            "stable"
        )
    }


def normalize_score(raw_score: float, scale_min: float = 1, scale_max: float = 5) -> float:
    """
    FIX: I-D1 (Sprint 5) — Normalize scores to 0-100 scale for cross-type comparison.
    """
    if scale_max == scale_min:
        return 50.0
    normalized = ((raw_score - scale_min) / (scale_max - scale_min)) * 100
    return round(max(0, min(100, normalized)), 1)
