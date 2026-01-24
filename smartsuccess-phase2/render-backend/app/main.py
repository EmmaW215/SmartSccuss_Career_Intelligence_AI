"""
SmartSuccess.AI Interview Backend - Phase 2
===========================================
Cost-Optimized Architecture:
- Render Free Tier ($0/month)
- Gemini API (Free tier + fallback)
- GPU Server (Self-hosted STT/TTS)
- Edge-TTS (Free fallback)

Monthly Cost: $0-10
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.routes import health, screening, behavioral, technical, customize, voice, dashboard


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lightweight startup for Render Free tier (<512MB RAM)"""
    print("🚀 SmartSuccess Interview Backend Starting...")
    print(f"📍 Environment: {settings.environment}")
    print(f"🔗 GPU Server: {settings.gpu_server_url or 'Not configured'}")
    print(f"🤖 LLM: {settings.llm_provider} (Gemini Free Tier)")
    
    # Load lightweight question banks (JSON files)
    from app.rag.question_bank import load_all_question_banks
    app.state.question_banks = load_all_question_banks()
    total_questions = sum(len(q) for q in app.state.question_banks.values())
    print(f"📚 Loaded {total_questions} questions from banks")
    
    # Initialize in-memory session store
    from app.services.session_store import SessionStore
    app.state.session_store = SessionStore()
    print("💾 Session store initialized (in-memory)")
    
    yield
    
    # Cleanup
    from app.services.gpu_client import get_gpu_client
    gpu_client = get_gpu_client()
    await gpu_client.close()
    print("👋 Shutdown complete")


app = FastAPI(
    title="SmartSuccess.AI Interview Backend",
    description="AI Mock Interview Platform - Phase 2 (Cost Optimized)",
    version="2.0.0",
    lifespan=lifespan
)

# CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An error occurred",
            "tip": "If GPU services are unavailable, text mode is still functional"
        }
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(screening.router, prefix="/api/interview/screening", tags=["Screening"])
app.include_router(behavioral.router, prefix="/api/interview/behavioral", tags=["Behavioral"])
app.include_router(technical.router, prefix="/api/interview/technical", tags=["Technical"])
app.include_router(customize.router, prefix="/api/interview/customize", tags=["Customize"])
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])


@app.get("/")
async def root():
    """Root endpoint with system status"""
    from app.services.gpu_client import get_gpu_client
    from app.services.llm_service import get_llm_service
    
    gpu_client = get_gpu_client()
    gpu_status = await gpu_client.check_health()
    
    llm_service = get_llm_service()
    llm_stats = llm_service.get_usage_stats()
    
    return {
        "service": "SmartSuccess.AI Interview Backend",
        "version": "2.0.0",
        "architecture": "Cost-Optimized (Render Free + Gemini + GPU)",
        "monthly_cost": "$0-10",
        "status": {
            "render": "online",
            "gpu_server": "online" if gpu_status.get("available") else "offline",
            "llm_provider": llm_stats.get("primary_provider", "gemini"),
            "gemini_free_remaining": llm_stats.get("free_tier_remaining", 0)
        },
        "features": {
            "screening_interview": True,
            "behavioral_interview": True,
            "technical_interview": True,
            "customize_interview": gpu_status.get("available", False),
            "voice_mode": gpu_status.get("available", False),
            "text_mode": True
        },
        "note": "Voice features require GPU server. Text mode always works."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "development"
    )
