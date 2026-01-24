"""
Multi-Provider LLM Service (Phase 2)
Supports both OpenAI (default) and Gemini (cost-optimized mode)

Default behavior: Uses OpenAI (existing behavior)
Cost-optimized mode: Uses Gemini when cost_optimized_mode=True
"""

import os
from typing import Optional, Dict, Any, List
from datetime import date
import httpx

from app.config import settings


class LLMService:
    """
    Multi-provider LLM service with automatic fallback
    
    Default: OpenAI (maintains existing behavior)
    Cost-optimized: Gemini 2.0 Flash (FREE tier) → Gemini 1.5 Flash → GPT-4o-mini
    """
    
    def __init__(self):
        self.gemini_api_key = settings.gemini_api_key
        self.openai_api_key = settings.openai_api_key
        self.cost_optimized = settings.cost_optimized_mode
        
        # Track daily usage for Gemini free tier
        self._daily_requests = 0
        self._last_reset_date: Optional[date] = None
        self._free_tier_limit = 1500
        
        # Gemini API endpoint
        self.gemini_base_url = "https://generativelanguage.googleapis.com/v1beta"
    
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
                if provider_config["provider"] == "gemini":
                    return await self._generate_gemini(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        model=provider_config["model"],
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                elif provider_config["provider"] == "openai":
                    return await self._generate_openai(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        model=provider_config["model"],
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
            except Exception as e:
                last_error = e
                print(f"LLM {provider_config['provider']}/{provider_config['model']} failed: {e}")
                continue
        
        raise Exception(f"All LLM providers failed. Last error: {last_error}")
    
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
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
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
                raise Exception(f"Gemini API error {response.status_code}: {response.text[:200]}")
            
            data = response.json()
            
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                self._daily_requests += 1
                return text
            except (KeyError, IndexError):
                raise Exception(f"Failed to parse Gemini response: {data}")
    
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
                raise Exception(f"OpenAI API error: {response.text[:200]}")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
    
    def _get_provider_order(self, force_provider: Optional[str]) -> List[Dict]:
        """Get ordered list of providers based on cost and availability"""
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
        
        # Cost-optimized order
        providers = []
        
        if self.gemini_api_key and self._daily_requests < self._free_tier_limit:
            providers.append(config["primary"])
        
        if self.gemini_api_key:
            providers.append(config["fallback"])
        
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
        return {
            "daily_requests": self._daily_requests,
            "free_tier_limit": self._free_tier_limit,
            "free_tier_remaining": max(0, self._free_tier_limit - self._daily_requests),
            "primary_provider": "gemini" if (self.cost_optimized and self.gemini_api_key) else "openai",
            "cost_optimized_mode": self.cost_optimized,
            "gemini_configured": bool(self.gemini_api_key),
            "openai_configured": bool(self.openai_api_key)
        }


# Singleton
_llm_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get singleton LLM service instance"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMService()
    return _llm_instance
