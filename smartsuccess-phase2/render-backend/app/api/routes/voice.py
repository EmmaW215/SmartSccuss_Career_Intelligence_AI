"""
Voice Service Endpoints
STT (Speech-to-Text) and TTS (Text-to-Speech)
Uses GPU server with Edge-TTS fallback
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

from app.services.gpu_client import get_gpu_client, VoiceProvider


router = APIRouter()


class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "professional"
    emotion: Optional[str] = None


@router.get("/status")
async def get_voice_status():
    """Check voice service availability"""
    gpu_client = get_gpu_client()
    status = await gpu_client.check_health()
    
    tts_available = status.get("available") and status.get("services", {}).get("tts", True)
    stt_available = status.get("available") and status.get("services", {}).get("stt", True)
    
    return {
        "voice_enabled": status.get("available", False),
        "tts": {
            "available": tts_available or True,  # Edge-TTS always available
            "provider": "gpu" if tts_available else "edge_tts",
            "quality": "high" if tts_available else "standard"
        },
        "stt": {
            "available": stt_available,
            "provider": "gpu" if stt_available else "none",
            "note": "STT requires GPU server" if not stt_available else None
        },
        "gpu_latency_ms": status.get("latency_ms")
    }


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("en")
):
    """
    Transcribe audio to text
    Requires GPU server (no fallback for STT)
    """
    gpu_client = get_gpu_client()
    
    # Read audio data
    audio_data = await audio.read()
    
    if len(audio_data) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")
    
    if len(audio_data) > 25 * 1024 * 1024:  # 25MB limit
        raise HTTPException(status_code=400, detail="Audio file too large (max 25MB)")
    
    try:
        transcript, provider = await gpu_client.transcribe(audio_data, language)
        
        return {
            "text": transcript,
            "provider": provider.value,
            "language": language
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Transcription failed: {str(e)}. Voice input requires GPU server."
        )


@router.post("/synthesize")
async def synthesize_speech(body: SynthesizeRequest):
    """
    Synthesize text to speech
    Uses GPU XTTS or falls back to Edge-TTS
    """
    gpu_client = get_gpu_client()
    
    if not body.text or len(body.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text is required")
    
    if len(body.text) > 5000:
        raise HTTPException(status_code=400, detail="Text too long (max 5000 characters)")
    
    try:
        audio_data, provider = await gpu_client.synthesize(
            text=body.text,
            voice=body.voice,
            emotion=body.emotion
        )
        
        # Return audio as streaming response
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav" if provider == VoiceProvider.GPU else "audio/mp3",
            headers={
                "X-Voice-Provider": provider.value,
                "X-Voice-Quality": "high" if provider == VoiceProvider.GPU else "standard"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Speech synthesis failed: {str(e)}"
        )


@router.post("/synthesize-url")
async def synthesize_speech_url(body: SynthesizeRequest):
    """
    Synthesize text and return as base64 data URL
    Useful for frontend audio playback
    """
    gpu_client = get_gpu_client()
    
    if not body.text or len(body.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text is required")
    
    try:
        audio_data, provider = await gpu_client.synthesize(
            text=body.text,
            voice=body.voice,
            emotion=body.emotion
        )
        
        import base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        mime_type = "audio/wav" if provider == VoiceProvider.GPU else "audio/mp3"
        
        return {
            "audio_url": f"data:{mime_type};base64,{audio_base64}",
            "provider": provider.value,
            "quality": "high" if provider == VoiceProvider.GPU else "standard"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Speech synthesis failed: {str(e)}"
        )


@router.get("/voices")
async def list_available_voices():
    """List available voice profiles"""
    gpu_client = get_gpu_client()
    status = await gpu_client.check_health()
    
    gpu_voices = []
    if status.get("available"):
        gpu_voices = [
            {"id": "professional", "name": "Professional Alex", "style": "neutral", "quality": "high"},
            {"id": "friendly", "name": "Friendly Alex", "style": "cheerful", "quality": "high"},
            {"id": "calm", "name": "Calm Alex", "style": "calm", "quality": "high"}
        ]
    
    edge_voices = [
        {"id": "en-US-AriaNeural", "name": "Aria (US)", "style": "neutral", "quality": "standard"},
        {"id": "en-US-GuyNeural", "name": "Guy (US)", "style": "neutral", "quality": "standard"},
        {"id": "en-GB-SoniaNeural", "name": "Sonia (UK)", "style": "neutral", "quality": "standard"}
    ]
    
    return {
        "gpu_available": status.get("available", False),
        "gpu_voices": gpu_voices,
        "fallback_voices": edge_voices,
        "recommended": "professional" if status.get("available") else "en-US-AriaNeural"
    }
