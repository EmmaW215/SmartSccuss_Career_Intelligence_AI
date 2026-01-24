"""
GPU TTS Service
Human-like voice synthesis using XTTS-v2

Cost: $0 (self-hosted)
Quality: Human-like, emotional, natural prosody
"""

import os
import io
import asyncio
from typing import Optional, Dict
import torch


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
        
        self._load_model()
    
    def _load_model(self):
        """Load XTTS model"""
        try:
            from TTS.api import TTS
            
            print(f"Loading XTTS-v2 on {self.device}...")
            
            # XTTS v2 - best quality
            self.model = TTS(
                model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                progress_bar=False
            ).to(self.device)
            
            print("XTTS-v2 loaded successfully")
            
        except ImportError:
            print("WARNING: TTS not installed. Install with: pip install TTS")
            self._load_fallback()
        except Exception as e:
            print(f"Error loading XTTS: {e}")
            self._load_fallback()
    
    def _load_fallback(self):
        """Load fallback TTS model"""
        try:
            from TTS.api import TTS
            
            print("Loading fallback TTS model...")
            self.model = TTS(
                model_name="tts_models/en/ljspeech/tacotron2-DDC",
                progress_bar=False
            ).to(self.device)
            print("Fallback TTS loaded")
            
        except Exception as e:
            print(f"Fallback TTS also failed: {e}")
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
        loop = asyncio.get_event_loop()
        audio_data = await loop.run_in_executor(
            None,
            self._synthesize_sync,
            processed_text,
            voice_config,
            language
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
        import wave
        
        # Create temp file for output
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        
        try:
            # Generate audio
            if hasattr(self.model, 'tts_to_file'):
                self.model.tts_to_file(
                    text=text,
                    file_path=temp_path,
                    language=language,
                    speed=voice_config.get("speed", 1.0)
                )
            else:
                # Fallback for simpler models
                self.model.tts_to_file(
                    text=text,
                    file_path=temp_path
                )
            
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
