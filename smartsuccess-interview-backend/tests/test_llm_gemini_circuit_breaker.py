"""
Tests for the Gemini 429 circuit breaker in LLMService._get_provider_order.

Goal: when Gemini's account quota is exhausted (429), stop wasting two Gemini
round-trips on every call. The breaker skips Gemini for a cooldown window,
then retries. Crucially: when Gemini is healthy the chain is unchanged, and
non-cost-optimized (OpenAI-only) behavior is untouched.
"""

import time

import pytest

from app.services.llm_service import LLMService


def _providers(service):
    return [(p["provider"], p["model"]) for p in service._get_provider_order(None)]


def _make_service(monkeypatch, gemini=True, groq=True, openai=True):
    service = LLMService()
    service.cost_optimized = True
    service.gemini_api_key = "g" if gemini else None
    service.groq_api_key = "q" if groq else None
    service.openai_api_key = "o" if openai else None
    service._daily_requests = 0
    return service


class TestProviderOrderUnchangedWhenHealthy:
    def test_default_chain_is_gemini_gemini_groq_openai(self, monkeypatch):
        service = _make_service(monkeypatch)
        order = _providers(service)
        assert [p for p, _ in order] == ["gemini", "gemini", "groq", "openai"]

    def test_breaker_does_not_engage_without_a_429(self, monkeypatch):
        service = _make_service(monkeypatch)
        assert service._gemini_in_cooldown() is False
        assert [p for p, _ in _providers(service)].count("gemini") == 2


class TestCircuitBreakerSkipsGeminiAfter429:
    def test_open_breaker_skips_both_gemini_levels(self, monkeypatch):
        service = _make_service(monkeypatch)
        # Simulate a 429 having opened the breaker.
        service._gemini_cooldown_until = time.monotonic() + 900

        order = [p for p, _ in _providers(service)]
        assert "gemini" not in order
        assert order == ["groq", "openai"]

    def test_breaker_expires_and_gemini_returns(self, monkeypatch):
        service = _make_service(monkeypatch)
        service._gemini_cooldown_until = time.monotonic() - 1  # already expired
        assert service._gemini_in_cooldown() is False
        assert [p for p, _ in _providers(service)].count("gemini") == 2

    def test_gemini_only_still_tried_during_cooldown(self, monkeypatch):
        """Safety net: never return an empty chain when Gemini is all we have."""
        service = _make_service(monkeypatch, groq=False, openai=False)
        service._gemini_cooldown_until = time.monotonic() + 900
        order = _providers(service)
        assert order, "must still attempt Gemini rather than fail with no provider"
        assert all(p == "gemini" for p, _ in order)


class TestForcedAndDefaultPathsUntouched:
    def test_force_openai_unaffected_by_cooldown(self, monkeypatch):
        service = _make_service(monkeypatch)
        service._gemini_cooldown_until = time.monotonic() + 900
        order = service._get_provider_order("openai")
        assert [p["provider"] for p in order] == ["openai"]

    def test_force_gemini_still_honored(self, monkeypatch):
        """Explicit force_provider='gemini' is honored — breaker only governs
        the automatic chain, so no caller behavior silently changes."""
        service = _make_service(monkeypatch)
        service._gemini_cooldown_until = time.monotonic() + 900
        order = service._get_provider_order("gemini")
        assert order and all(p["provider"] == "gemini" for p in order)


class TestGenerate429OpensBreaker:
    @pytest.mark.asyncio
    async def test_429_response_sets_cooldown(self, monkeypatch):
        import httpx

        service = _make_service(monkeypatch)
        assert service._gemini_in_cooldown() is False

        class _Resp:
            status_code = 429
            text = '{"error": {"code": 429, "message": "quota exceeded"}}'

        class _Client:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def post(self, *args, **kwargs):
                return _Resp()

        monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: _Client())

        with pytest.raises(Exception):
            await service._generate_gemini(
                prompt="hi", system_prompt=None, model="gemini-2.5-flash",
                temperature=0.3, max_tokens=100,
            )
        assert service._gemini_in_cooldown() is True
        # Next provider order now skips Gemini
        assert "gemini" not in [p for p, _ in _providers(service)]


class TestNonCostOptimizedUntouched:
    @pytest.mark.asyncio
    async def test_default_mode_still_calls_openai_only(self, monkeypatch):
        service = LLMService()
        service.cost_optimized = False
        service.openai_api_key = "o"

        called = {}

        async def _fake_openai(prompt, system_prompt, model, temperature, max_tokens):
            called["openai"] = True
            return "ok"

        monkeypatch.setattr(service, "_generate_openai", _fake_openai)
        result = await service.generate("hi")
        assert result == "ok"
        assert called.get("openai") is True
