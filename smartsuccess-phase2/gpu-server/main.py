"""
SmartSuccess.AI GPU Server
Self-hosted GPU services for STT, TTS, and Custom RAG

Services:
- STT: Whisper Large-v3 (高精度语音识别)
- TTS: XTTS-v2 (人声级别输出)
- RAG: Custom RAG Builder (用户文档处理)

Cost: $0 (self-hosted, only electricity)
"""

import os
import torch
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import io

from services.whisper_service import WhisperService
from services.tts_service import TTSService
from services.rag_service import RAGService


# Global service instances
whisper_service: Optional[WhisperService] = None
tts_service: Optional[TTSService] = None
rag_service: Optional[RAGService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup"""
    global whisper_service, tts_service, rag_service
    
    print("🚀 Starting SmartSuccess GPU Server")
    print(f"🔧 CUDA available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"🎮 GPU: {torch.cuda.get_device_name(0)}")
        print(f"💾 GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    
    # Load services
    print("📥 Loading Whisper Large-v3...")
    whisper_service = WhisperService()
    print("✅ Whisper loaded")
    
    print("📥 Loading XTTS-v2...")
    tts_service = TTSService()
    print("✅ TTS loaded")
    
    print("📥 Initializing RAG Service...")
    rag_service = RAGService()
    print("✅ RAG service ready")
    
    print("🎉 GPU Server ready!")
    
    yield
    
    print("👋 Shutting down GPU Server...")


app = FastAPI(
    title="SmartSuccess GPU Server",
    description="GPU-accelerated STT, TTS, and RAG services",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    gpu_available = torch.cuda.is_available()
    
    return {
        "status": "healthy",
        "gpu_available": gpu_available,
        "gpu_name": torch.cuda.get_device_name(0) if gpu_available else None,
        "services": {
            "stt": whisper_service is not None,
            "tts": tts_service is not None,
            "rag": rag_service is not None
        }
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "SmartSuccess GPU Server",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "stt": "/api/stt/transcribe",
            "tts": "/api/tts/synthesize",
            "rag": "/api/rag/build"
        }
    }


# ==================== STT Endpoints ====================

@app.post("/api/stt/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("en")
):
    """
    Transcribe audio to text using Whisper Large-v3
    
    Args:
        audio: Audio file (webm, wav, mp3, etc.)
        language: Language code (en, zh, etc.) or "auto"
    """
    if whisper_service is None:
        raise HTTPException(status_code=503, detail="Whisper service not available")
    
    # Read audio
    audio_data = await audio.read()
    
    if len(audio_data) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")
    
    # Transcribe
    try:
        result = await whisper_service.transcribe(
            audio_data=audio_data,
            language=language if language != "auto" else None
        )
        
        return {
            "text": result["text"],
            "language": result["language"],
            "confidence": result.get("confidence", 0.9),
            "provider": "gpu-whisper-large-v3"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# ==================== TTS Endpoints ====================

class TTSRequest(BaseModel):
    text: str
    voice: str = "professional"
    emotion: Optional[str] = None
    language: str = "en"


@app.post("/api/tts/synthesize")
async def synthesize_speech(body: TTSRequest):
    """
    Synthesize text to speech using XTTS-v2
    
    Args:
        text: Text to synthesize
        voice: Voice profile (professional, friendly, calm)
        emotion: Optional emotion (happy, calm, serious)
        language: Language code
    """
    if tts_service is None:
        raise HTTPException(status_code=503, detail="TTS service not available")
    
    if not body.text or len(body.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text is required")
    
    if len(body.text) > 5000:
        raise HTTPException(status_code=400, detail="Text too long (max 5000 chars)")
    
    try:
        audio_data = await tts_service.synthesize(
            text=body.text,
            voice=body.voice,
            emotion=body.emotion,
            language=body.language
        )
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav",
            headers={
                "X-Voice-Provider": "gpu-xtts-v2",
                "X-Voice-Quality": "high"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


@app.get("/api/tts/voices")
async def list_voices():
    """List available TTS voices"""
    return {
        "voices": [
            {"id": "professional", "name": "Professional Alex", "style": "neutral"},
            {"id": "friendly", "name": "Friendly Alex", "style": "cheerful"},
            {"id": "calm", "name": "Calm Alex", "style": "calm"}
        ],
        "default": "professional"
    }


# ==================== RAG Endpoints ====================

@app.post("/api/rag/build")
async def build_custom_rag(
    user_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    Build custom RAG from user documents
    
    Args:
        user_id: User identifier
        files: Document files (PDF, TXT, MD, DOCX)
    """
    if rag_service is None:
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 files allowed")
    
    # Process files
    processed_files = []
    for file in files:
        content = await file.read()
        
        if len(content) > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds 10MB limit"
            )
        
        processed_files.append({
            "filename": file.filename,
            "content": content,
            "content_type": file.content_type
        })
    
    try:
        result = await rag_service.build(
            user_id=user_id,
            files=processed_files
        )
        
        return {
            "success": True,
            "user_id": user_id,
            "profile": result["profile"],
            "questions": result["questions"],
            "provider": "gpu"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG build failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False
    )
