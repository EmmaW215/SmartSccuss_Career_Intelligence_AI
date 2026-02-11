"""
Voice API Routes
Speech-to-text and text-to-speech endpoints

Phase 2 Enhancement: Adds GPU server support with graceful fallback to OpenAI
Default behavior: Uses OpenAI (existing behavior)
Phase 2 mode: Uses GPU server when available, falls back to OpenAI or Edge-TTS
"""

import io
import base64
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional

from app.core.voice_service import VoiceService, get_voice_service
from app.interview.screening_interview import get_screening_interview_service
from app.interview.behavioral_interview import get_behavioral_interview_service
from app.interview.technical_interview import get_technical_interview_service
from app.config import settings

# Phase 2: Optional GPU client
try:
    from app.services.gpu_client import get_gpu_client, VoiceProvider
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    get_gpu_client = None
    VoiceProvider = None

router = APIRouter(
    prefix="/api/voice",
    tags=["voice"]
)


def get_service() -> VoiceService:
    """Get voice service instance"""
    return get_voice_service()


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form(default="en")
):
    """
    Transcribe audio to text using Whisper
    
    Phase 2: Tries GPU server first (if enabled), falls back to OpenAI
    Default: Uses OpenAI (existing behavior)
    
    - **audio**: Audio file (mp3, wav, webm, m4a, etc.)
    - **language**: ISO language code (default: en)
    """
    # Read audio data once upfront so both GPU and fallback paths can use it
    audio_data = await audio.read()
    
    # Phase 2: Try GPU server if enabled
    if GPU_AVAILABLE and getattr(settings, 'use_gpu_voice', False):
        try:
            gpu_client = get_gpu_client()
            transcript, provider = await gpu_client.transcribe(audio_data, language)
            return {
                "text": transcript,
                "language": language,
                "provider": provider.value if provider else "gpu"
            }
        except Exception as e:
            # Fallback to OpenAI if GPU fails
            print(f"GPU transcription failed, falling back to OpenAI: {e}")
    
    # Default: Use OpenAI (existing behavior)
    voice_service = get_service()
    
    if not voice_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Voice service not available (missing API key)"
        )
    
    try:
        text = await voice_service.transcribe(audio_data, language)
        
        return {
            "text": text,
            "language": language,
            "provider": "openai"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthesize")
async def synthesize_speech(
    text: str = Form(...),
    voice: str = Form(default="alloy"),
    speed: float = Form(default=1.0)
):
    """
    Synthesize text to speech
    
    Phase 2: Tries GPU server first (if enabled), falls back to Edge-TTS or OpenAI
    Default: Uses OpenAI (existing behavior)
    
    - **text**: Text to synthesize
    - **voice**: Voice option (alloy, echo, fable, onyx, nova, shimmer for OpenAI; professional, friendly, calm for GPU)
    - **speed**: Speech speed (0.25 to 4.0) - OpenAI only
    
    Returns audio file.
    """
    # Phase 2: Try GPU server if enabled
    if GPU_AVAILABLE and getattr(settings, 'use_gpu_voice', False):
        try:
            gpu_client = get_gpu_client()
            audio_data, provider = await gpu_client.synthesize(
                text=text,
                voice=voice if voice in ["professional", "friendly", "calm"] else "professional"
            )
            mime_type = "audio/wav" if provider == VoiceProvider.GPU else "audio/mp3"
            return StreamingResponse(
                io.BytesIO(audio_data),
                media_type=mime_type,
                headers={
                    "Content-Disposition": "attachment; filename=response.wav",
                    "X-Voice-Provider": provider.value
                }
            )
        except Exception as e:
            # Fallback to OpenAI if GPU fails
            print(f"GPU synthesis failed, falling back to OpenAI: {e}")
    
    # Default: Use OpenAI (existing behavior)
    voice_service = get_service()
    
    if not voice_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Voice service not available (missing API key)"
        )
    
    try:
        audio_data = await voice_service.synthesize(text, voice, speed)
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=response.mp3",
                "X-Voice-Provider": "openai"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthesize/base64")
async def synthesize_speech_base64(
    text: str = Form(...),
    voice: str = Form(default="alloy"),
    speed: float = Form(default=1.0)
):
    """
    Synthesize text to speech and return as base64
    
    Useful for web applications that need to play audio directly.
    """
    voice_service = get_service()
    
    if not voice_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Voice service not available (missing API key)"
        )
    
    try:
        audio_data = await voice_service.synthesize(text, voice, speed)
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        
        return {
            "audio_base64": audio_base64,
            "mime_type": "audio/mpeg"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interview/{interview_type}/voice-turn")
async def voice_interview_turn(
    interview_type: str,
    session_id: str = Form(...),
    audio: UploadFile = File(...),
    language: str = Form(default="en"),
    voice: str = Form(default="alloy")
):
    """
    Complete voice interview turn:
    1. Transcribe user audio
    2. Process through interview service
    3. Synthesize response audio
    
    - **interview_type**: screening, behavioral, or technical
    - **session_id**: Session identifier
    - **audio**: User's audio input
    - **language**: Language for transcription
    - **voice**: Voice for synthesis
    
    Returns both text and audio response.
    """
    voice_service = get_service()
    
    if not voice_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Voice service not available (missing API key)"
        )
    
    # Get appropriate interview service
    service_map = {
        "screening": get_screening_interview_service,
        "behavioral": get_behavioral_interview_service,
        "technical": get_technical_interview_service
    }
    
    if interview_type not in service_map:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown interview type: {interview_type}. Use: screening, behavioral, or technical"
        )
    
    interview_service = service_map[interview_type]()
    
    # Check session exists
    session = interview_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    try:
        # Read audio
        audio_data = await audio.read()
        
        # Step 1: Transcribe
        user_text = await voice_service.transcribe(audio_data, language)
        
        # Step 2: Process through interview service
        response = await interview_service.process_message(session_id, user_text)
        response_text = response.message
        
        # Step 3: Synthesize response
        response_audio = await voice_service.synthesize(response_text, voice)
        response_audio_base64 = base64.b64encode(response_audio).decode("utf-8")
        
        return {
            "user_transcript": user_text,
            "assistant_response": response_text,
            "response_type": response.type,
            "question_number": response.question_number,
            "total_questions": response.total_questions,
            "evaluation": response.evaluation,
            "audio_base64": response_audio_base64,
            "audio_mime_type": "audio/mpeg"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voices")
async def get_available_voices():
    """Get list of available TTS voices"""
    return {
        "voices": [
            {"id": "alloy", "description": "Neutral, balanced voice"},
            {"id": "echo", "description": "Warm, conversational voice"},
            {"id": "fable", "description": "Expressive, storytelling voice"},
            {"id": "onyx", "description": "Deep, authoritative voice"},
            {"id": "nova", "description": "Energetic, upbeat voice"},
            {"id": "shimmer", "description": "Clear, gentle voice"}
        ],
        "default": "alloy"
    }


@router.get("/status")
async def get_voice_service_status():
    """Check voice service availability"""
    voice_service = get_service()
    
    status = {
        "available": voice_service.is_available(),
        "whisper_model": voice_service.whisper_model,
        "tts_model": voice_service.tts_model,
        "default_voice": voice_service.default_voice,
        "provider": "openai"
    }
    
    # Phase 2: Add GPU status if available
    if GPU_AVAILABLE:
        try:
            gpu_client = get_gpu_client()
            gpu_status = await gpu_client.check_health()
            status["gpu"] = {
                "available": gpu_status.get("available", False),
                "services": gpu_status.get("services", {}),
                "latency_ms": gpu_status.get("latency_ms")
            }
            if gpu_status.get("available") and getattr(settings, 'use_gpu_voice', False):
                status["provider"] = "gpu"
        except Exception:
            status["gpu"] = {"available": False, "error": "GPU client not initialized"}
    
    return status
