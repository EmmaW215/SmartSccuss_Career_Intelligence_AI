"""
GPU Whisper Service
High-accuracy STT using faster-whisper (CTranslate2) Large-v3

Cost: $0 (self-hosted)
Quality: same large-v3 weights as openai-whisper, ~4x faster / ~4x less VRAM
Languages: 99+ languages supported

Phase 4 PR 4-1: swapped openai-whisper -> faster-whisper. The transcribe()
return shape ({text, language, segments, confidence}) is unchanged, so
main.py's /api/stt/transcribe response and the Render-side gpu_client.py
need zero changes.
"""

import os
import logging
import tempfile
import time
import asyncio
from typing import Optional, Dict, Any

logger = logging.getLogger("gpu.stt.whisper")


def _detect_device() -> str:
    """Prefer CUDA when available; torch is imported lazily so this module
    can be imported (for contract tests) without torch installed."""
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


class WhisperService:
    """
    GPU-accelerated faster-whisper for high-accuracy transcription

    Model: whisper-large-v3 (CTranslate2)
    - int8_float16 on CUDA (~3.5 GB VRAM) / int8 on CPU
    - Multi-language support, VAD filtering
    """

    def __init__(self, model_size: str = "large-v3"):
        self.device = _detect_device()
        self.model_size = model_size
        # compute_type: GPU default int8_float16; CPU needs int8.
        # Override via WHISPER_COMPUTE (PRD: CPU-offload-friendly fallback).
        self.compute_type = os.getenv("WHISPER_COMPUTE") or (
            "int8_float16" if self.device == "cuda" else "int8"
        )
        self.model = None

        self._load_model()

    def _load_model(self):
        """Load the faster-whisper model"""
        try:
            from faster_whisper import WhisperModel

            logger.info(
                "Loading faster-whisper %s on %s (compute=%s)...",
                self.model_size, self.device, self.compute_type,
            )
            t0 = time.perf_counter()
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info(
                "faster-whisper loaded successfully in %.1fs",
                time.perf_counter() - t0,
            )

        except ImportError:
            logger.error(
                "faster-whisper package not installed — STT will be unavailable"
            )
            self.model = None
        except Exception as e:
            logger.error("Failed to load faster-whisper model: %s", e)
            self.model = None
    
    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text
        
        Args:
            audio_data: Audio bytes (webm, wav, mp3, etc.)
            language: Language code or None for auto-detect
            
        Returns:
            Dict with text, language, segments, confidence
        """
        if self.model is None:
            raise Exception("Whisper model not loaded")
        
        # Write to temp file (Whisper requires file path)
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name
        
        logger.debug("Temp audio file written — %d bytes → %s", len(audio_data), temp_path)
        
        try:
            # Run transcription in thread pool (CPU-bound)
            t0 = time.perf_counter()
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._transcribe_sync,
                temp_path,
                language
            )
            inference_ms = (time.perf_counter() - t0) * 1000
            
            logger.debug(
                "Whisper inference — %.0fms | segments=%d",
                inference_ms, len(result.get("segments", [])),
            )
            
            return result
            
        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def _transcribe_sync(
        self,
        audio_path: str,
        language: Optional[str]
    ) -> Dict[str, Any]:
        """Synchronous transcription via faster-whisper.

        faster-whisper returns (segments_generator, info); the generator is
        lazy, so iterating it is what actually runs inference. We normalize the
        segments back into the same dict shape the openai-whisper path emitted
        ({start, end, text, avg_logprob}) so downstream consumers and the
        confidence calc are unchanged.
        """
        segments_iter, info = self.model.transcribe(
            audio_path,
            task="transcribe",
            language=language,        # None -> auto-detect
            vad_filter=True,          # PRD: drop non-speech, improves accuracy
            word_timestamps=True,
        )

        segments = []
        text_parts = []
        for seg in segments_iter:
            text_parts.append(seg.text)
            segments.append({
                "start": getattr(seg, "start", 0.0),
                "end": getattr(seg, "end", 0.0),
                "text": seg.text,
                "avg_logprob": getattr(seg, "avg_logprob", 0.0),
            })

        detected_language = getattr(info, "language", None) or language or "en"

        return {
            "text": "".join(text_parts).strip(),
            "language": detected_language,
            "segments": segments,
            "confidence": self._calculate_confidence({"segments": segments}),
        }
    
    def _calculate_confidence(self, result: Dict) -> float:
        """Calculate average confidence from segments"""
        segments = result.get("segments", [])
        if not segments:
            return 0.9
        
        confidences = []
        for seg in segments:
            if "avg_logprob" in seg:
                # Convert log prob to confidence (0-1)
                conf = min(1.0, max(0.0, 1.0 + seg["avg_logprob"]))
                confidences.append(conf)
        
        return sum(confidences) / len(confidences) if confidences else 0.9
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages"""
        return [
            "en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr",
            "pl", "ca", "nl", "ar", "sv", "it", "id", "hi", "fi", "vi",
            "he", "uk", "el", "ms", "cs", "ro", "da", "hu", "ta", "no",
            "th", "ur", "hr", "bg", "lt", "la", "mi", "ml", "cy", "sk",
            "te", "fa", "lv", "bn", "sr", "az", "sl", "kn", "et", "mk",
            "br", "eu", "is", "hy", "ne", "mn", "bs", "kk", "sq", "sw",
            "gl", "mr", "pa", "si", "km", "sn", "yo", "so", "af", "oc",
            "ka", "be", "tg", "sd", "gu", "am", "yi", "lo", "uz", "fo",
            "ht", "ps", "tk", "nn", "mt", "sa", "lb", "my", "bo", "tl",
            "mg", "as", "tt", "haw", "ln", "ha", "ba", "jw", "su"
        ]
