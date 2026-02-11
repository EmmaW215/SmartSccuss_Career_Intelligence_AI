"""
GPU TTS Service
Human-like voice synthesis using XTTS-v2

Cost: $0 (self-hosted)
Quality: Human-like, emotional, natural prosody
"""

import os
import io
import logging
import time
import asyncio
from typing import Optional, Dict
import torch

logger = logging.getLogger("gpu.tts.engine")


class TTSService:
    """
    GPU-accelerated TTS using XTTS-v2
    
    Features:
    - Human-like voice quality
    - Emotion injection
    - Natural prosody and rhythm
    - Multi-language support
    - Voice cloning capability
    """
    
    # Voice profiles
    VOICES = {
        "professional": {
            "speaker_wav": None,  # Use default
            "speed": 1.0,
            "temperature": 0.7
        },
        "friendly": {
            "speaker_wav": None,
            "speed": 1.05,
            "temperature": 0.8
        },
        "calm": {
            "speaker_wav": None,
            "speed": 0.95,
            "temperature": 0.6
        }
    }
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.is_multilingual = False
        self.is_multi_speaker = False
        self.default_speaker = None
        
        self._load_model()
    
    def _load_model(self):
        """Load XTTS model with timeout fallback"""
        try:
            from TTS.api import TTS
            
            # Try XTTS-v2 first (multilingual, best quality)
            try:
                logger.info("Attempting XTTS-v2 on %s (best quality)...", self.device)
                t0 = time.perf_counter()
                self.model = TTS(
                    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                    progress_bar=False
                ).to(self.device)
                self.is_multilingual = True
                logger.info("XTTS-v2 loaded in %.1fs (multilingual)", time.perf_counter() - t0)
                return
            except Exception as e:
                logger.warning("DEGRADATION: XTTS-v2 failed — %s — trying VITS fallback", e)
            
            # Try VITS multilingual (lighter, still multilingual)
            try:
                logger.info("Attempting VITS multilingual (fallback #1)...")
                t0 = time.perf_counter()
                self.model = TTS(
                    model_name="tts_models/multilingual/multi-dataset/your_tts",
                    progress_bar=False
                ).to(self.device)
                self.is_multilingual = True
                self.is_multi_speaker = True
                self.default_speaker = "male-en-2"
                logger.info(
                    "VITS multilingual loaded in %.1fs (speaker: %s)",
                    time.perf_counter() - t0, self.default_speaker,
                )
                return
            except Exception as e:
                logger.warning("DEGRADATION: VITS multilingual failed — %s — trying English-only fallback", e)
            
            # Fallback to English-only model
            self._load_fallback()
            
        except ImportError:
            logger.error("TTS package not installed — attempting minimal fallback")
            self._load_fallback()
    
    def _load_fallback(self):
        """Load fallback TTS model (English only)"""
        try:
            from TTS.api import TTS
            
            logger.warning("DEGRADATION: Loading tacotron2-DDC (English only, lowest quality)...")
            t0 = time.perf_counter()
            self.model = TTS(
                model_name="tts_models/en/ljspeech/tacotron2-DDC",
                progress_bar=False
            ).to(self.device)
            self.is_multilingual = False
            logger.warning(
                "Fallback TTS loaded in %.1fs — English only, reduced quality",
                time.perf_counter() - t0,
            )
            
        except Exception as e:
            logger.critical("ALL TTS models failed — TTS will be unavailable: %s", e)
            self.model = None
    
    async def synthesize(
        self,
        text: str,
        voice: str = "professional",
        emotion: Optional[str] = None,
        language: str = "en"
    ) -> bytes:
        """
        Synthesize text to speech
        
        Args:
            text: Text to synthesize
            voice: Voice profile (professional, friendly, calm)
            emotion: Optional emotion hint
            language: Language code
            
        Returns:
            Audio bytes (WAV format)
        """
        if self.model is None:
            raise Exception("TTS model not loaded")
        
        # Get voice config
        voice_config = self.VOICES.get(voice, self.VOICES["professional"])
        
        # Preprocess text for natural speech
        processed_text = self._preprocess_text(text)
        
        # Apply emotion if specified
        if emotion:
            processed_text = self._apply_emotion(processed_text, emotion)
        
        # Run synthesis in thread pool
        t0 = time.perf_counter()
        loop = asyncio.get_event_loop()
        audio_data = await loop.run_in_executor(
            None,
            self._synthesize_sync,
            processed_text,
            voice_config,
            language
        )
        inference_ms = (time.perf_counter() - t0) * 1000
        
        logger.debug(
            "TTS inference — %.0fms | %d chars → %d bytes",
            inference_ms, len(processed_text), len(audio_data),
        )
        
        return audio_data
    
    def _synthesize_sync(
        self,
        text: str,
        voice_config: Dict,
        language: str
    ) -> bytes:
        """Synchronous synthesis"""
        import tempfile
        
        # Create temp file for output
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        
        try:
            # Build kwargs based on model capabilities
            kwargs = {
                "text": text,
                "file_path": temp_path,
            }
            
            if self.is_multilingual:
                kwargs["language"] = language
                speed = voice_config.get("speed", 1.0)
                if speed != 1.0:
                    kwargs["speed"] = speed
            
            if self.is_multi_speaker and self.default_speaker:
                kwargs["speaker"] = self.default_speaker
            
            # Generate audio
            self.model.tts_to_file(**kwargs)
            
            # Read audio data
            with open(temp_path, "rb") as f:
                audio_data = f.read()
            
            return audio_data
            
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for natural speech"""
        # Add pauses at natural break points
        text = text.replace("...", ", ")
        
        # Expand some abbreviations
        replacements = {
            "AI": "A.I.",
            "API": "A.P.I.",
            "UI": "U.I.",
            "UX": "U.X.",
            "ML": "M.L.",
            "NLP": "N.L.P."
        }
        
        for abbr, expanded in replacements.items():
            text = text.replace(f" {abbr} ", f" {expanded} ")
        
        return text
    
    def _apply_emotion(self, text: str, emotion: str) -> str:
        """
        Apply emotion hints to text
        
        Note: XTTS doesn't have explicit emotion control,
        but we can add speech patterns that suggest emotion
        """
        # For now, return text as-is
        # Future: Add SSML or other emotion markers
        return text
    
    def get_available_voices(self) -> list:
        """Get available voice profiles"""
        return [
            {
                "id": "professional",
                "name": "Professional Alex",
                "description": "Clear, professional tone for business contexts"
            },
            {
                "id": "friendly",
                "name": "Friendly Alex", 
                "description": "Warm, approachable tone"
            },
            {
                "id": "calm",
                "name": "Calm Alex",
                "description": "Relaxed, soothing tone"
            }
        ]
    
    def get_supported_languages(self) -> list:
        """Get supported languages for XTTS"""
        return [
            "en",  # English
            "es",  # Spanish
            "fr",  # French
            "de",  # German
            "it",  # Italian
            "pt",  # Portuguese
            "pl",  # Polish
            "tr",  # Turkish
            "ru",  # Russian
            "nl",  # Dutch
            "cs",  # Czech
            "ar",  # Arabic
            "zh",  # Chinese
            "ja",  # Japanese
            "hu",  # Hungarian
            "ko"   # Korean
        ]
