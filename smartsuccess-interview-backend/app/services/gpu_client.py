"""
GPU Server Client
Handles communication with self-hosted GPU server for STT/TTS/RAG
Falls back to Edge-TTS (FREE) when GPU unavailable

FIXES APPLIED:
- E-A2 (Sprint 1): text-mode fallback when GPU STT fails
                    (previously raised hard exception, now returns guidance)
"""

import time
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class VoiceProvider(Enum):
    GPU = "gpu"              # Self-hosted, best quality
    EDGE_TTS = "edge_tts"    # Free Microsoft TTS
    NONE = "none"            # Text-only mode


@dataclass
class GPUStatus:
    available: bool
    latency_ms: Optional[float] = None
    services: Optional[Dict[str, bool]] = None
    last_check: float = 0
    error: Optional[str] = None


class GPUClient:
    """
    Client for GPU server communication

    Services (all FREE, self-hosted):
    - STT: Whisper Large-v3 (high accuracy)
    - TTS: XTTS-v2 (human-like voice)
    - RAG: Custom document processing

    Fallback (FREE):
    - Edge-TTS: Microsoft's free TTS API
    """

    def __init__(self):
        self.gpu_url = settings.gpu_server_url
        self.timeout = settings.gpu_server_timeout
        self.health_cache_ttl = settings.gpu_health_check_interval

        self._status_cache: Optional[GPUStatus] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=self.timeout)
        return self._http_client

    async def check_health(self, force: bool = False) -> Dict[str, Any]:
        """Check GPU server health with caching"""
        current_time = time.time()

        # Use cache if fresh
        if not force and self._status_cache:
            if (current_time - self._status_cache.last_check
                    < self.health_cache_ttl):
                return {
                    "available": self._status_cache.available,
                    "latency_ms": self._status_cache.latency_ms,
                    "services": self._status_cache.services,
                    "cached": True
                }

        # No GPU URL configured
        if not self.gpu_url:
            self._status_cache = GPUStatus(
                available=False,
                last_check=current_time,
                error="GPU server URL not configured"
            )
            return {
                "available": False,
                "error": "GPU server not configured",
                "fallback": "text_mode"
            }

        # Check GPU server
        try:
            client = await self._get_client()
            start = time.time()

            response = await client.get(
                f"{self.gpu_url}/health", timeout=5.0
            )
            latency = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                self._status_cache = GPUStatus(
                    available=True,
                    latency_ms=latency,
                    services=data.get(
                        "services",
                        {"stt": True, "tts": True, "rag": True}
                    ),
                    last_check=current_time
                )
                return {
                    "available": True,
                    "latency_ms": latency,
                    "services": self._status_cache.services,
                    "gpu_name": data.get("gpu_name", "Unknown")
                }
        except Exception as e:
            self._status_cache = GPUStatus(
                available=False,
                last_check=current_time,
                error=str(e)
            )

        return {
            "available": False,
            "error": (
                self._status_cache.error
                if self._status_cache else "Unknown error"
            ),
            "fallback": "edge_tts"
        }

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "en"
    ) -> Tuple[str, VoiceProvider]:
        """
        Transcribe audio using GPU Whisper

        FIX: E-A2 (Sprint 1) — Graceful text-mode fallback instead of hard exception.
        Returns guidance message when STT unavailable.
        """
        status = await self.check_health()

        if (status.get("available")
                and status.get("services", {}).get("stt", True)):
            try:
                transcript = await self._gpu_transcribe(audio_data, language)
                return transcript, VoiceProvider.GPU
            except Exception as e:
                logger.warning(f"GPU STT failed: {e}")

        # FIX: E-A2 — Return guidance instead of raising hard exception
        # This lets the frontend gracefully switch to text input
        return (
            "[VOICE_UNAVAILABLE] Speech-to-text is currently unavailable. "
            "Please switch to text input mode.",
            VoiceProvider.NONE
        )

    async def synthesize(
        self,
        text: str,
        voice: str = "professional",
        emotion: Optional[str] = None
    ) -> Tuple[bytes, VoiceProvider]:
        """
        Synthesize text to speech

        Priority: GPU XTTS → Edge-TTS (free)
        """
        status = await self.check_health()

        # Try GPU first (best quality)
        if (status.get("available")
                and status.get("services", {}).get("tts", True)):
            try:
                audio = await self._gpu_synthesize(text, voice, emotion)
                return audio, VoiceProvider.GPU
            except Exception as e:
                logger.warning(f"GPU TTS failed: {e}")

        # Fallback to Edge-TTS (FREE)
        try:
            audio = await self._edge_tts_synthesize(text)
            return audio, VoiceProvider.EDGE_TTS
        except Exception as e:
            logger.warning(f"Edge-TTS failed: {e}")
            raise Exception(
                "Text-to-speech unavailable. All providers failed."
            )

    async def build_custom_rag(
        self,
        user_id: str,
        files: list
    ) -> Dict[str, Any]:
        """Build custom RAG on GPU server"""
        status = await self.check_health()

        if not status.get("available"):
            raise Exception(
                "Custom RAG requires GPU server. "
                "Please ensure GPU server is running."
            )

        try:
            client = await self._get_client()

            files_data = []
            for i, file_info in enumerate(files):
                content = file_info["content"]
                if isinstance(content, str):
                    content = content.encode()
                files_data.append((
                    "files",
                    (
                        file_info.get("filename", f"file_{i}"),
                        content,
                        file_info.get(
                            "content_type",
                            "application/octet-stream"
                        )
                    )
                ))

            response = await client.post(
                f"{self.gpu_url}/api/rag/build",
                files=files_data,
                data={"user_id": user_id},
                timeout=120.0
            )

            if response.status_code != 200:
                raise Exception(
                    f"RAG build failed: {response.text[:200]}"
                )

            return response.json()
        except httpx.TimeoutException:
            raise Exception(
                "RAG building timed out. Try smaller documents."
            )

    async def _gpu_transcribe(
        self, audio_data: bytes, language: str
    ) -> str:
        """Transcribe using GPU Whisper"""
        client = await self._get_client()

        response = await client.post(
            f"{self.gpu_url}/api/stt/transcribe",
            files={
                "audio": ("audio.webm", audio_data, "audio/webm")
            },
            data={"language": language},
            timeout=30.0
        )

        if response.status_code != 200:
            raise Exception(f"GPU STT error: {response.text[:200]}")

        return response.json().get("text", "")

    async def _gpu_synthesize(
        self,
        text: str,
        voice: str,
        emotion: Optional[str]
    ) -> bytes:
        """Synthesize using GPU XTTS"""
        client = await self._get_client()

        response = await client.post(
            f"{self.gpu_url}/api/tts/synthesize",
            json={
                "text": text,
                "voice": voice,
                "emotion": emotion,
                "model": "xtts-v2"
            },
            timeout=30.0
        )

        if response.status_code != 200:
            raise Exception(f"GPU TTS error: {response.text[:200]}")

        return response.content

    async def _edge_tts_synthesize(self, text: str) -> bytes:
        """Fallback TTS using Microsoft Edge-TTS (FREE)"""
        try:
            import edge_tts

            voice = settings.edge_tts_voice
            communicate = edge_tts.Communicate(text, voice)

            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

            return b"".join(audio_chunks)
        except ImportError:
            raise Exception(
                "edge-tts not installed. Run: pip install edge-tts"
            )

    async def close(self):
        """Close HTTP client"""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None


# Singleton
_gpu_client: Optional[GPUClient] = None


def get_gpu_client() -> GPUClient:
    """Get singleton GPU client instance"""
    global _gpu_client
    if _gpu_client is None:
        _gpu_client = GPUClient()
    return _gpu_client
