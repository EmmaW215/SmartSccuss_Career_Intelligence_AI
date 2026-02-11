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
import logging
import time
import torch
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import io

from services.logging_config import setup_logging
from services.whisper_service import WhisperService
from services.tts_service import TTSService
from services.rag_service import RAGService
from services.metrics import metrics

# Initialize logging BEFORE anything else
setup_logging()
logger = logging.getLogger("gpu.server")


# Global service instances
whisper_service: Optional[WhisperService] = None
tts_service: Optional[TTSService] = None
rag_service: Optional[RAGService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load models on startup"""
    global whisper_service, tts_service, rag_service
    
    logger.info("Starting SmartSuccess GPU Server v1.1.0")
    logger.info("CUDA available: %s", torch.cuda.is_available())
    
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
        logger.info("GPU: %s | VRAM: %.1f GB", gpu_name, gpu_mem)
    
    # Load services
    logger.info("Loading Whisper Large-v3...")
    t0 = time.perf_counter()
    whisper_service = WhisperService()
    logger.info("Whisper loaded in %.1fs", time.perf_counter() - t0)
    
    logger.info("Loading TTS model...")
    t0 = time.perf_counter()
    tts_service = TTSService()
    logger.info("TTS loaded in %.1fs", time.perf_counter() - t0)
    
    logger.info("Initializing RAG Service...")
    t0 = time.perf_counter()
    rag_service = RAGService()
    logger.info("RAG service ready in %.1fs", time.perf_counter() - t0)
    
    logger.info("GPU Server ready — all models loaded")
    
    yield
    
    logger.info("Shutting down GPU Server...")


app = FastAPI(
    title="SmartSuccess GPU Server",
    description="GPU-accelerated STT, TTS, and RAG services",
    version="1.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://smartsccuss-career-intelligence-ai.onrender.com",
        "https://smart-sccuss-career-intelligence-ai.vercel.app",
        "http://localhost:8000",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Metrics Middleware ====================

_req_logger = logging.getLogger("gpu.requests")

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Automatically track request count, latency, and errors for every API call."""
    path = request.url.path
    method = request.method
    # Skip metrics collection for health/metrics/docs endpoints themselves
    skip_paths = {"/health", "/health/detail", "/metrics", "/docs", "/openapi.json", "/"}
    if path in skip_paths:
        return await call_next(request)

    start = time.perf_counter()
    try:
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000
        success = response.status_code < 400
        metrics.record_request(
            endpoint=path,
            latency_ms=latency_ms,
            success=success,
            error_message=None if success else f"HTTP {response.status_code}",
        )
        # Structured request log
        if success:
            _req_logger.info(
                "%s %s — %d — %.1fms",
                method, path, response.status_code, latency_ms,
            )
        else:
            _req_logger.warning(
                "%s %s — %d — %.1fms",
                method, path, response.status_code, latency_ms,
            )
        return response
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        metrics.record_request(
            endpoint=path,
            latency_ms=latency_ms,
            success=False,
            error_message=str(exc)[:200],
        )
        _req_logger.error(
            "%s %s — EXCEPTION — %.1fms — %s",
            method, path, latency_ms, str(exc)[:150],
        )
        raise


# ==================== Health & Monitoring Endpoints ====================

def _model_status() -> dict:
    """Detailed per-model load status."""
    stt_status = "loaded"
    if whisper_service is None:
        stt_status = "not_initialized"
    elif whisper_service.model is None:
        stt_status = "failed"

    tts_status = "loaded"
    tts_model_name = "unknown"
    if tts_service is None:
        tts_status = "not_initialized"
    elif tts_service.model is None:
        tts_status = "failed"
    else:
        if tts_service.is_multilingual and tts_service.is_multi_speaker:
            tts_model_name = "VITS multilingual (your_tts)"
        elif tts_service.is_multilingual:
            tts_model_name = "XTTS-v2"
        else:
            tts_model_name = "tacotron2-DDC (English only)"

    rag_status = "loaded"
    rag_details = {}
    if rag_service is None:
        rag_status = "not_initialized"
    else:
        rag_details["embedding_model"] = "loaded" if rag_service.embedding_model else "failed"
        rag_details["chromadb"] = "connected" if rag_service.chroma_client else "unavailable"

    return {
        "stt": {
            "status": stt_status,
            "model": whisper_service.model_size if whisper_service else None,
            "device": whisper_service.device if whisper_service else None,
        },
        "tts": {
            "status": tts_status,
            "model": tts_model_name,
            "multilingual": tts_service.is_multilingual if tts_service else False,
            "multi_speaker": tts_service.is_multi_speaker if tts_service else False,
            "device": tts_service.device if tts_service else None,
        },
        "rag": {
            "status": rag_status,
            **rag_details,
            "device": rag_service.device if rag_service else None,
        },
    }


@app.get("/health")
async def health_check():
    """
    Quick health check — returns lightweight status.
    Use /health/detail for full GPU metrics and request stats.
    """
    gpu_available = torch.cuda.is_available()
    summary = metrics.get_summary()

    return {
        "status": "healthy",
        "gpu_available": gpu_available,
        "gpu_name": torch.cuda.get_device_name(0) if gpu_available else None,
        "uptime_seconds": metrics.get_uptime_seconds(),
        "services": {
            "stt": whisper_service is not None and whisper_service.model is not None,
            "tts": tts_service is not None and tts_service.model is not None,
            "rag": rag_service is not None,
        },
        "requests": {
            "total": summary["total_requests"],
            "errors": summary["total_errors"],
            "error_rate_pct": summary["error_rate_pct"],
        },
        "last_success_time": summary["last_success_time"],
    }


@app.get("/health/detail")
async def health_detail():
    """
    Detailed health check with full GPU metrics, model status,
    per-service request stats, and last successful request times.
    """
    gpu_info = metrics.get_gpu_metrics()
    summary = metrics.get_summary()

    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": metrics.get_uptime_seconds(),
        "gpu": gpu_info,
        "models": _model_status(),
        "requests": {
            "total": summary["total_requests"],
            "total_success": summary["total_success"],
            "total_errors": summary["total_errors"],
            "error_rate_pct": summary["error_rate_pct"],
            "last_success_time": summary["last_success_time"],
            "by_service": summary["services"],
        },
    }


@app.get("/metrics")
async def get_metrics():
    """
    Full per-endpoint metrics for monitoring / ops dashboard.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": metrics.get_uptime_seconds(),
        "gpu": metrics.get_gpu_metrics(),
        "endpoints": metrics.get_endpoint_stats(),
        "summary": metrics.get_summary(),
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "SmartSuccess GPU Server",
        "version": "1.1.0",
        "endpoints": {
            "health": "/health",
            "health_detail": "/health/detail",
            "metrics": "/metrics",
            "stt": "/api/stt/transcribe",
            "tts": "/api/tts/synthesize",
            "rag": "/api/rag/build",
        },
    }


# ==================== STT Endpoints ====================

_stt_logger = logging.getLogger("gpu.stt")

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
        _stt_logger.error("Transcribe request rejected — Whisper service not available")
        raise HTTPException(status_code=503, detail="Whisper service not available")
    
    # Read audio
    audio_data = await audio.read()
    audio_size_kb = len(audio_data) / 1024
    
    if len(audio_data) == 0:
        _stt_logger.warning("Transcribe request rejected — empty audio file")
        raise HTTPException(status_code=400, detail="Empty audio file")
    
    _stt_logger.info(
        "STT request — lang=%s audio=%.1fKB filename=%s",
        language, audio_size_kb, audio.filename,
    )
    
    # Transcribe
    t0 = time.perf_counter()
    try:
        result = await whisper_service.transcribe(
            audio_data=audio_data,
            language=language if language != "auto" else None
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        
        text_preview = result["text"][:80].replace("\n", " ")
        _stt_logger.info(
            "STT complete — %.0fms | lang=%s conf=%.2f | \"%s%s\"",
            elapsed_ms, result["language"], result.get("confidence", 0.9),
            text_preview, "..." if len(result["text"]) > 80 else "",
        )
        
        return {
            "text": result["text"],
            "language": result["language"],
            "confidence": result.get("confidence", 0.9),
            "provider": "gpu-whisper-large-v3"
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        _stt_logger.error("STT failed — %.0fms — %s", elapsed_ms, str(e))
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


# ==================== TTS Endpoints ====================

class TTSRequest(BaseModel):
    text: str
    voice: str = "professional"
    emotion: Optional[str] = None
    language: str = "en"


_tts_logger = logging.getLogger("gpu.tts")

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
        _tts_logger.error("Synthesize request rejected — TTS service not available")
        raise HTTPException(status_code=503, detail="TTS service not available")
    
    if not body.text or len(body.text.strip()) == 0:
        _tts_logger.warning("Synthesize request rejected — empty text")
        raise HTTPException(status_code=400, detail="Text is required")
    
    if len(body.text) > 5000:
        _tts_logger.warning("Synthesize request rejected — text too long (%d chars)", len(body.text))
        raise HTTPException(status_code=400, detail="Text too long (max 5000 chars)")
    
    _tts_logger.info(
        "TTS request — voice=%s lang=%s emotion=%s chars=%d",
        body.voice, body.language, body.emotion, len(body.text),
    )
    
    t0 = time.perf_counter()
    try:
        audio_data = await tts_service.synthesize(
            text=body.text,
            voice=body.voice,
            emotion=body.emotion,
            language=body.language
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        audio_size_kb = len(audio_data) / 1024
        
        _tts_logger.info(
            "TTS complete — %.0fms | voice=%s lang=%s | %d chars → %.1fKB audio",
            elapsed_ms, body.voice, body.language, len(body.text), audio_size_kb,
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
        elapsed_ms = (time.perf_counter() - t0) * 1000
        _tts_logger.error("TTS failed — %.0fms — %s", elapsed_ms, str(e))
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

_rag_logger = logging.getLogger("gpu.rag")

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
        _rag_logger.error("RAG build rejected — service not available")
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    if len(files) == 0:
        _rag_logger.warning("RAG build rejected — no files provided")
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 5:
        _rag_logger.warning("RAG build rejected — too many files (%d)", len(files))
        raise HTTPException(status_code=400, detail="Maximum 5 files allowed")
    
    filenames = [f.filename for f in files]
    _rag_logger.info("RAG build — user=%s files=%d (%s)", user_id, len(files), ", ".join(filenames))
    
    # Process files
    processed_files = []
    for file in files:
        content = await file.read()
        
        if len(content) > 10 * 1024 * 1024:  # 10MB
            _rag_logger.warning("RAG build rejected — file %s exceeds 10MB", file.filename)
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds 10MB limit"
            )
        
        processed_files.append({
            "filename": file.filename,
            "content": content,
            "content_type": file.content_type
        })
    
    t0 = time.perf_counter()
    try:
        result = await rag_service.build(
            user_id=user_id,
            files=processed_files
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        
        _rag_logger.info(
            "RAG build complete — %.0fms | user=%s docs=%d questions=%d rag_id=%s",
            elapsed_ms, user_id, result.get("document_count", 0),
            len(result.get("questions", [])), result.get("rag_id"),
        )
        
        return {
            "success": True,
            "user_id": user_id,
            "profile": result["profile"],
            "questions": result["questions"],
            "rag_id": result.get("rag_id"),
            "provider": "gpu"
        }
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000
        _rag_logger.error("RAG build failed — %.0fms — user=%s — %s", elapsed_ms, user_id, str(e))
        raise HTTPException(status_code=500, detail=f"RAG build failed: {str(e)}")


@app.get("/api/rag/profile/{user_id}")
async def get_user_profile(user_id: str):
    """Retrieve a stored user profile and questions"""
    if rag_service is None:
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    profile = await rag_service.get_user_profile(user_id)
    if profile is None:
        _rag_logger.info("Profile not found — user=%s", user_id)
        raise HTTPException(status_code=404, detail=f"No profile found for user {user_id}")
    
    _rag_logger.info("Profile retrieved — user=%s", user_id)
    return profile


@app.post("/api/rag/query")
async def query_documents(
    user_id: str = Form(...),
    query: str = Form(...),
    n_results: int = Form(default=3)
):
    """Query stored documents using semantic search"""
    if rag_service is None:
        raise HTTPException(status_code=503, detail="RAG service not available")
    
    t0 = time.perf_counter()
    results = await rag_service.query_documents(user_id, query, n_results)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    
    _rag_logger.info(
        "RAG query — %.0fms | user=%s results=%d | \"%s\"",
        elapsed_ms, user_id, len(results), query[:60],
    )
    return {
        "user_id": user_id,
        "query": query,
        "results": results,
        "count": len(results)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
