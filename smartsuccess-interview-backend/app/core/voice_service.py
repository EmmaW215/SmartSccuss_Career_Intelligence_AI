"""
Voice Service for SmartSuccess Interview Backend
Provides speech-to-text (Whisper) and text-to-speech (OpenAI TTS)

Features:
- Whisper ASR for transcription
- OpenAI TTS for speech synthesis
- Multiple voice options
- Streaming support
"""

import os
import io
from typing import Optional, Tuple, AsyncGenerator
from openai import AsyncOpenAI

from app.config import settings


class VoiceService:
    """
    Voice service for speech-to-text and text-to-speech
    
    Usage:
        service = VoiceService()
        text = await service.transcribe(audio_bytes)
        audio = await service.synthesize("Hello world")
    """
    
    # Available voices for TTS
    VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    
    def __init__(self):
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = AsyncOpenAI(api_key=api_key)
        else:
            self.client = None
            print("Warning: OpenAI API key not set, voice service disabled")
        
        self.whisper_model = settings.whisper_model
        self.tts_model = settings.tts_model
        self.default_voice = settings.tts_voice
    
    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "en",
        prompt: Optional[str] = None
    ) -> str:
        """
        Transcribe audio to text using Whisper
        
        Args:
            audio_data: Audio file bytes (supports mp3, wav, webm, m4a, etc.)
            language: ISO language code (e.g., "en", "zh", "es")
            prompt: Optional prompt to guide transcription
            
        Returns:
            Transcribed text
        """
        if not self.client:
            raise RuntimeError("Voice service not initialized (missing API key)")
        
        try:
            # Create a file-like object from bytes
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.webm"  # Default filename
            
            kwargs = {
                "model": self.whisper_model,
                "file": audio_file,
                "language": language,
                "response_format": "text"
            }
            
            if prompt:
                kwargs["prompt"] = prompt
            
            transcript = await self.client.audio.transcriptions.create(**kwargs)
            
            return transcript.strip() if isinstance(transcript, str) else str(transcript).strip()
            
        except Exception as e:
            print(f"Transcription error: {e}")
            raise
    
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0
    ) -> bytes:
        """
        Synthesize text to speech using OpenAI TTS
        
        Args:
            text: Text to synthesize
            voice: Voice option (alloy, echo, fable, onyx, nova, shimmer)
            speed: Speech speed (0.25 to 4.0)
            
        Returns:
            Audio bytes (MP3 format)
        """
        if not self.client:
            raise RuntimeError("Voice service not initialized (missing API key)")
        
        # Validate voice
        voice = voice or self.default_voice
        if voice not in self.VOICES:
            voice = self.default_voice
        
        # Clamp speed
        speed = max(0.25, min(4.0, speed))
        
        try:
            response = await self.client.audio.speech.create(
                model=self.tts_model,
                voice=voice,
                input=text,
                speed=speed
            )
            
            return response.content
            
        except Exception as e:
            print(f"TTS error: {e}")
            raise
    
    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized speech for lower latency
        
        Yields:
            Chunks of audio bytes
        """
        if not self.client:
            raise RuntimeError("Voice service not initialized (missing API key)")
        
        voice = voice or self.default_voice
        if voice not in self.VOICES:
            voice = self.default_voice
        
        speed = max(0.25, min(4.0, speed))
        
        try:
            async with self.client.audio.speech.with_streaming_response.create(
                model=self.tts_model,
                voice=voice,
                input=text,
                speed=speed
            ) as response:
                async for chunk in response.iter_bytes(chunk_size=4096):
                    yield chunk
                    
        except Exception as e:
            print(f"TTS streaming error: {e}")
            raise
    
    async def transcribe_and_respond(
        self,
        audio_data: bytes,
        process_callback,
        language: str = "en",
        voice: Optional[str] = None
    ) -> Tuple[str, str, bytes]:
        """
        Full voice pipeline: transcribe → process → synthesize
        
        Args:
            audio_data: User's audio input
            process_callback: Async function to process transcribed text
            language: Language for transcription
            voice: Voice for synthesis
            
        Returns:
            Tuple of (transcribed_text, response_text, response_audio)
        """
        # Step 1: Transcribe user audio
        user_text = await self.transcribe(audio_data, language)
        
        # Step 2: Process the text (interview service callback)
        response_text = await process_callback(user_text)
        
        # Step 3: Synthesize response
        response_audio = await self.synthesize(response_text, voice)
        
        return user_text, response_text, response_audio
    
    def is_available(self) -> bool:
        """Check if voice service is available"""
        return self.client is not None


# Singleton instance
_voice_service_instance: Optional[VoiceService] = None


def get_voice_service() -> VoiceService:
    """Get the singleton voice service instance"""
    global _voice_service_instance
    if _voice_service_instance is None:
        _voice_service_instance = VoiceService()
    return _voice_service_instance
