"""
LangGraph LLM model factory.

This module provides a consistent chat-model builder for graph nodes with:
- OpenAI default behavior (backward-compatible)
- Optional cost-optimized fallback chain (Gemini -> Groq -> OpenAI)
- Tier presets for standard/eval/cheap node workloads
"""

from __future__ import annotations

import logging
from typing import Any, Literal, Optional

from app.config import settings

try:
    from langchain_groq import ChatGroq
except (ImportError, ModuleNotFoundError):  # pragma: no cover - optional dependency
    ChatGroq = None  # type: ignore[assignment]

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except (ImportError, ModuleNotFoundError):  # pragma: no cover - optional dependency
    ChatGoogleGenerativeAI = None  # type: ignore[assignment]

try:
    from langchain_openai import ChatOpenAI
except (ImportError, ModuleNotFoundError):  # pragma: no cover - optional dependency
    ChatOpenAI = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

TierName = Literal["standard", "eval", "cheap"]


def _tier_defaults(tier: TierName) -> tuple[float, int]:
    if tier == "eval":
        return 0.2, min(int(getattr(settings, "llm_max_tokens", 1024)), 900)
    if tier == "cheap":
        return 0.4, min(int(getattr(settings, "llm_max_tokens", 1024)), 600)
    return float(getattr(settings, "llm_temperature", 0.7)), int(
        getattr(settings, "llm_max_tokens", 1024)
    )


def _build_openai_model(
    temperature: float,
    max_tokens: int,
    model_name: Optional[str] = None,
) -> Optional[Any]:
    if ChatOpenAI is None or not settings.openai_api_key:
        return None
    try:
        return ChatOpenAI(
            model=model_name or settings.llm_model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.openai_api_key,
        )
    except Exception as exc:
        logger.warning("Failed to initialize OpenAI chat model: %s", exc)
        return None


def _build_gemini_model(
    temperature: float,
    max_tokens: int,
    model_name: Optional[str] = None,
) -> Optional[Any]:
    if ChatGoogleGenerativeAI is None or not settings.gemini_api_key:
        return None
    try:
        return ChatGoogleGenerativeAI(
            model=model_name or settings.gemini_model_primary,
            temperature=temperature,
            max_output_tokens=max_tokens,
            google_api_key=settings.gemini_api_key,
        )
    except Exception as exc:
        logger.warning("Failed to initialize Gemini chat model: %s", exc)
        return None


def _build_groq_model(
    temperature: float,
    max_tokens: int,
    model_name: Optional[str] = None,
) -> Optional[Any]:
    if ChatGroq is None or not settings.groq_api_key:
        return None
    try:
        return ChatGroq(
            model=model_name or "llama-3.3-70b-versatile",
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.groq_api_key,
        )
    except Exception as exc:
        logger.warning("Failed to initialize Groq chat model: %s", exc)
        return None


def _required_model_or_error(model: Optional[Any], provider: str) -> Any:
    if model is None:
        raise RuntimeError(
            f"Requested provider '{provider}' is unavailable. "
            f"Check API key and langchain provider dependency."
        )
    return model


def get_chat_model(
    tier: TierName = "standard",
    *,
    force_provider: Optional[Literal["openai", "gemini", "groq"]] = None,
) -> Any:
    """
    Get a chat model for LangGraph nodes.

    Selection policy:
    - force_provider set: return that provider or raise
    - tier == eval: force OpenAI for structured-output reliability
    - cost_optimized_mode=False: OpenAI default
    - cost_optimized_mode=True: Gemini primary with Groq/OpenAI fallbacks
    """
    temperature, max_tokens = _tier_defaults(tier)
    if tier == "eval" and force_provider and force_provider != "openai":
        raise ValueError(
            "Eval tier requires OpenAI for structured output consistency. "
            "Use force_provider='openai' or omit force_provider."
        )

    if force_provider:
        if force_provider == "openai":
            return _required_model_or_error(
                _build_openai_model(temperature, max_tokens), "openai"
            )
        if force_provider == "gemini":
            return _required_model_or_error(
                _build_gemini_model(temperature, max_tokens), "gemini"
            )
        return _required_model_or_error(
            _build_groq_model(temperature, max_tokens), "groq"
        )

    # Eval tier: keep deterministic/structured behavior strongest.
    if tier == "eval":
        model = _build_openai_model(temperature, max_tokens)
        return _required_model_or_error(model, "openai")

    openai_model = _build_openai_model(temperature, max_tokens)
    if not settings.cost_optimized_mode:
        return _required_model_or_error(openai_model, "openai")

    gemini_model = _build_gemini_model(temperature, max_tokens)
    groq_model = _build_groq_model(temperature, max_tokens)

    # Build fallback chain (gemini -> groq -> openai) with available models only.
    candidates = [model for model in [gemini_model, groq_model, openai_model] if model]
    if not candidates:
        raise RuntimeError(
            "No LLM provider is configured for graph runtime. "
            "Set OPENAI_API_KEY and/or GEMINI_API_KEY/GROQ_API_KEY."
        )

    primary = candidates[0]
    fallback_models = candidates[1:]
    if fallback_models and hasattr(primary, "with_fallbacks"):
        logger.info(
            "Graph model fallback chain enabled: %s",
            " -> ".join(
                [
                    "gemini" if model is gemini_model else
                    "groq" if model is groq_model else
                    "openai"
                    for model in candidates
                ]
            ),
        )
        return primary.with_fallbacks(fallback_models)

    return primary
