"""
SmartSuccess.AI Interview Backend
Main FastAPI Application Entry Point

Provides specialized mock interview services:
- Screening Interview (10-15 min)
- Behavioral Interview (25-30 min) 
- Technical Interview (45 min)

Each with dedicated RAG, prompts, and evaluation criteria.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers
from app.api.routes import screening, behavioral, technical, voice, health

# Phase 2: Optional routes (only loaded if available)
try:
    from app.api.routes import customize, dashboard
    PHASE2_AVAILABLE = True
except ImportError:
    PHASE2_AVAILABLE = False
    customize = None
    dashboard = None

# MatchWise module: Optional (only loaded if dependencies available)
try:
    from app.api.routes import matchwise
    MATCHWISE_AVAILABLE = True
except ImportError as e:
    MATCHWISE_AVAILABLE = False
    matchwise = None
    print(f"⚠️  MatchWise module not loaded: {e}")

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize services
    print("🚀 Starting SmartSuccess Interview Backend...")
    print(f"📍 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    # Initialize RAG question banks
    from app.rag.screening_rag import ScreeningRAGService
    from app.rag.behavioral_rag import BehavioralRAGService
    from app.rag.technical_rag import TechnicalRAGService
    
    app.state.screening_rag = ScreeningRAGService()
    app.state.behavioral_rag = BehavioralRAGService()
    app.state.technical_rag = TechnicalRAGService()
    
    print("✅ RAG services initialized")
    print("✅ Interview services ready")
    
    # Phase 2: Initialize optional session store (for customize/dashboard features)
    try:
        from app.services.session_store import SessionStore
        from app.config import settings
        
        # Only initialize if Phase 2 features are enabled
        if getattr(settings, 'cost_optimized_mode', False) or getattr(settings, 'use_conversation_engine', True):
            app.state.session_store = SessionStore()
            print("✅ Phase 2 session store initialized")
    except Exception as e:
        print(f"⚠️  Phase 2 session store not initialized: {e}")
        app.state.session_store = None

    # Phase 2 Agent Tools: status logging (PRD 02_PHASE2_AGENT_TOOLS.md)
    try:
        from app.config import settings as _settings
        if _settings.use_agent_tools:
            print("🤖 Agent tools ENABLED (USE_AGENT_TOOLS=true) — "
                  f"tool_call_logs → {_settings.tool_call_log_dir}")
        if _settings.use_mcp_tools:
            print("🔌 MCP tools flag set (USE_MCP_TOOLS=true) — run the MCP "
                  "server with: python -m app.agent.mcp_server")
    except Exception as e:
        print(f"⚠️  Agent tools status check failed: {e}")

    yield
    
    # Shutdown
    print("👋 Shutting down SmartSuccess Interview Backend...")

# Create FastAPI app
app = FastAPI(
    title="SmartSuccess.AI Interview Backend",
    description="""
    AI-powered mock interview platform with specialized interview types:
    
    - **Screening Interview**: First impression assessment (10-15 min)
    - **Behavioral Interview**: STAR method evaluation (25-30 min)
    - **Technical Interview**: Technical skills assessment (45 min)
    
    Features:
    - Pre-trained question banks for each interview type
    - RAG-powered personalization with resume/JD context
    - Voice support (Whisper ASR + TTS)
    - Real-time feedback and scoring
    """,
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration - Improved parsing with fallback
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "").strip()

if allowed_origins_env:
    # Parse environment variable, handle spaces and empty values
    allowed_origins = [
        origin.strip() 
        for origin in allowed_origins_env.split(",") 
        if origin.strip()
    ]
else:
    # Fallback to hardcoded list if environment variable not set
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://smart-sccuss-career-intelligence-ai.vercel.app",
        "https://smartsuccess-ai.vercel.app",
        "https://smartsccuss-career-intelligence-ai.onrender.com",
    ]

# Debug logging (helpful for troubleshooting)
print(f"🌐 CORS Allowed Origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(screening.router)
app.include_router(behavioral.router)
app.include_router(technical.router)
app.include_router(voice.router)

# Phase 2: Include optional routers (only if available)
if PHASE2_AVAILABLE and customize and dashboard:
    app.include_router(customize.router)
    app.include_router(dashboard.router)
    print("✅ Phase 2 routes (customize, dashboard) enabled")

# MatchWise: Include MatchWise router (only if available)
if MATCHWISE_AVAILABLE and matchwise:
    app.include_router(matchwise.router)
    print("✅ MatchWise routes (/api/matchwise/*) enabled")

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "SmartSuccess.AI Interview Backend",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "screening": "/api/interview/screening",
            "behavioral": "/api/interview/behavioral",
            "technical": "/api/interview/technical",
            "voice": "/api/voice",
            "docs": "/docs"
        },
        "phase2_features": {
            "available": PHASE2_AVAILABLE,
            "customize": "/api/interview/customize" if PHASE2_AVAILABLE else None,
            "dashboard": "/api/dashboard" if PHASE2_AVAILABLE else None
        },
        "matchwise": {
            "available": MATCHWISE_AVAILABLE,
            "endpoints": "/api/matchwise" if MATCHWISE_AVAILABLE else None
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("ENVIRONMENT", "development") == "development"
    )
