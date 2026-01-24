"""
GPU Whisper Service
High-accuracy STT using Whisper Large-v3

Cost: $0 (self-hosted)
Quality: Best available
Languages: 99+ languages supported
"""

import os
import tempfile
import asyncio
from typing import Optional, Dict, Any

import torch


class WhisperService:
    """
    GPU-accelerated Whisper for high-accuracy transcription
    
    Model: whisper-large-v3
    - Best accuracy available
    - Multi-language support
    - Word-level timestamps
    """
    
    def __init__(self, model_size: str = "large-v3"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_size = model_size
        self.model = None
        
        self._load_model()
    
    def _load_model(self):
        """Load Whisper model"""
        try:
            import whisper
            
            print(f"Loading Whisper {self.model_size} on {self.device}...")
            self.model = whisper.load_model(self.model_size, device=self.device)
            print(f"Whisper loaded successfully")
            
        except ImportError:
            print("WARNING: whisper not installed. Install with: pip install openai-whisper")
            self.model = None
        except Exception as e:
            print(f"Error loading Whisper: {e}")
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
        
        try:
            # Run transcription in thread pool (CPU-bound)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._transcribe_sync,
                temp_path,
                language
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
        """Synchronous transcription"""
        options = {
            "task": "transcribe",
            "word_timestamps": True,
            "fp16": self.device == "cuda"
        }
        
        if language:
            options["language"] = language
        
        result = self.model.transcribe(audio_path, **options)
        
        return {
            "text": result["text"].strip(),
            "language": result.get("language", "en"),
            "segments": result.get("segments", []),
            "confidence": self._calculate_confidence(result)
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
