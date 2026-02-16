"""
Multi-Provider LLM Service (Phase 2 + Groq)
Supports OpenAI (default), Gemini (cost-optimized), and Groq/Llama (free fallback)

Default behavior: Uses OpenAI (existing behavior)
Cost-optimized mode: Gemini (free) → Groq/Llama (free) → OpenAI (paid, last resort)

FIXES APPLIED:
- A-Q2 (Sprint 2): This service is now the SINGLE entry point for all LLM calls.
                    All agents use base._call_llm() which routes through here.
- E-A2 (Sprint 1): Graceful degradation when GPU/LLM unavailable
- F-A3 (Sprint 5): Usage logging for cost tracking
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import date
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    Multi-provider LLM service with automatic fallback

    Default: OpenAI (maintains existing behavior)
    Cost-optimized: Gemini (free) → Groq/Llama (free) → OpenAI (paid, last resort)
    """

    def __init__(self):
        self.gemini_api_key = settings.gemini_api_key
        self.openai_api_key = settings.openai_api_key
        self.groq_api_key = settings.groq_api_key
        self.cost_optimized = settings.cost_optimized_mode

        # Track daily usage for Gemini free tier
        self._daily_requests = 0
        self._last_reset_date: Optional[date] = None
        self._free_tier_limit = 1500

        # FIX: F-A3 (Sprint 5) — Track per-provider usage for cost reporting
        self._provider_usage: Dict[str, int] = {
            "gemini": 0,
            "groq": 0,
            "openai": 0
        }

        # Gemini API endpoint
        self.gemini_base_url = (
            "https://generativelanguage.googleapis.com/v1beta"
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        force_provider: Optional[str] = None
    ) -> str:
        """
        Generate text using configured provider

        Default: OpenAI (existing behavior)
        Cost-optimized: Gemini (when cost_optimized_mode=True)
        """
        # Default behavior: Use OpenAI (existing)
        if not self.cost_optimized and not force_provider:
            return await self._generate_openai(
                prompt=prompt,
                system_prompt=system_prompt,
                model=settings.llm_model,
                temperature=temperature,
                max_tokens=max_tokens
            )

        # Cost-optimized mode: Try Gemini first
        self._check_daily_reset()
        providers = self._get_provider_order(force_provider)

        last_error = None
        for provider_config in providers:
            try:
                provider = provider_config["provider"]
                model = provider_config["model"]

                if provider == "gemini":
                    result = await self._generate_gemini(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                elif provider == "groq":
                    result = await self._generate_groq(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                elif provider == "openai":
                    result = await self._generate_openai(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                else:
                    continue

                # FIX: F-A3 — Track usage
                self._provider_usage[provider] = (
                    self._provider_usage.get(provider, 0) + 1
                )
                return result

            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM {provider_config['provider']}/{provider_config['model']} "
                    f"failed: {e}"
                )
                continue

        # FIX: E-A2 (Sprint 1) — Graceful error message
        raise Exception(
            f"All LLM providers failed. Last error: {last_error}. "
            f"Tried {len(providers)} providers. "
            f"Check API keys and rate limits."
        )

    async def _generate_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Gemini API"""
        if not self.gemini_api_key:
            raise Exception("Gemini API key not configured")

        contents = []

        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System: {system_prompt}"}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Understood. I'll follow these instructions."}]
            })

        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        url = f"{self.gemini_base_url}/models/{model}:generateContent"

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.95,
                "topK": 40
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT",
                 "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH",
                 "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                 "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                 "threshold": "BLOCK_NONE"}
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                params={"key": self.gemini_api_key},
                json=payload,
                timeout=30.0
            )

            if response.status_code != 200:
                raise Exception(
                    f"Gemini API error {response.status_code}: "
                    f"{response.text[:200]}"
                )

            data = response.json()

            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                self._daily_requests += 1
                return text
            except (KeyError, IndexError):
                raise Exception(
                    f"Failed to parse Gemini response: {data}"
                )

    async def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using OpenAI API (default/fallback)"""
        if not self.openai_api_key:
            raise Exception("OpenAI API key not configured")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=30.0
            )

            if response.status_code != 200:
                raise Exception(
                    f"OpenAI API error: {response.text[:200]}"
                )

            data = response.json()
            # FIX: F-A3 — Track usage
            self._provider_usage["openai"] = (
                self._provider_usage.get("openai", 0) + 1
            )
            return data["choices"][0]["message"]["content"]

    async def _generate_groq(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Groq API (Llama models, free tier)"""
        if not self.groq_api_key:
            raise Exception("Groq API key not configured")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=30.0
            )

            if response.status_code != 200:
                raise Exception(
                    f"Groq API error: {response.text[:200]}"
                )

            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _get_provider_order(
        self, force_provider: Optional[str]
    ) -> List[Dict]:
        """
        Get ordered list of providers based on cost and availability

        Cost-optimized chain:
        1. Gemini 2.0 Flash (free, 1500 req/day)
        2. Gemini 1.5 Flash (very cheap)
        3. Groq / Llama 3.3 70B (free, 14400 req/day)
        4. OpenAI GPT-4o-mini (paid, last resort)
        """
        from app.config import COST_OPTIMIZED_CONFIG

        config = COST_OPTIMIZED_CONFIG["llm"]

        if force_provider == "openai":
            return [config["emergency"]] if self.openai_api_key else []

        if force_provider == "gemini":
            providers = []
            if self.gemini_api_key:
                if self._daily_requests < self._free_tier_limit:
                    providers.append(config["primary"])
                providers.append(config["fallback"])
            return providers

        if force_provider == "groq":
            return (
                [config["groq_fallback"]] if self.groq_api_key else []
            )

        # Cost-optimized order: Gemini → Groq → OpenAI
        providers = []

        # Level 1: Gemini free tier
        if (self.gemini_api_key
                and self._daily_requests < self._free_tier_limit):
            providers.append(config["primary"])

        # Level 2: Gemini fallback model
        if self.gemini_api_key:
            providers.append(config["fallback"])

        # Level 3: Groq / Llama (free)
        if self.groq_api_key:
            providers.append(config["groq_fallback"])

        # Level 4: OpenAI (paid, last resort)
        if self.openai_api_key:
            providers.append(config["emergency"])

        return providers

    def _check_daily_reset(self):
        """Reset daily counter at midnight"""
        today = date.today()
        if self._last_reset_date != today:
            self._daily_requests = 0
            self._last_reset_date = today

    def get_usage_stats(self) -> Dict:
        """Get current usage statistics"""
        self._check_daily_reset()

        # Determine current primary provider
        if self.cost_optimized:
            if self.gemini_api_key:
                primary = "gemini"
            elif self.groq_api_key:
                primary = "groq"
            else:
                primary = "openai"
        else:
            primary = "openai"

        return {
            "daily_requests": self._daily_requests,
            "free_tier_limit": self._free_tier_limit,
            "free_tier_remaining": max(
                0, self._free_tier_limit - self._daily_requests
            ),
            "primary_provider": primary,
            "cost_optimized_mode": self.cost_optimized,
            "fallback_chain": (
                "gemini → groq → openai"
                if self.cost_optimized else "openai only"
            ),
            "gemini_configured": bool(self.gemini_api_key),
            "groq_configured": bool(self.groq_api_key),
            "openai_configured": bool(self.openai_api_key),
            # FIX: F-A3 — Per-provider usage breakdown
            "provider_usage": dict(self._provider_usage)
        }


# Singleton
_llm_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get singleton LLM service instance"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMService()
    return _llm_instance
