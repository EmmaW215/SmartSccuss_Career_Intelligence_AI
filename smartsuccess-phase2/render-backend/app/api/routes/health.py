"""
Health Check Endpoints
"""

from fastapi import APIRouter, Request

from app.services.gpu_client import get_gpu_client
from app.services.llm_service import get_llm_service


router = APIRouter()


@router.get("/health")
async def health_check(request: Request):
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "SmartSuccess.AI Interview Backend",
        "version": "2.0.0"
    }


@router.get("/health/detailed")
async def detailed_health(request: Request):
    """Detailed health check with all services"""
    gpu_client = get_gpu_client()
    llm_service = get_llm_service()
    
    gpu_status = await gpu_client.check_health(force=True)
    llm_stats = llm_service.get_usage_stats()
    
    session_stats = {}
    if hasattr(request.app.state, 'session_store'):
        session_stats = request.app.state.session_store.get_stats()
    
    return {
        "status": "healthy",
        "services": {
            "render_backend": {
                "status": "online",
                "tier": "free"
            },
            "gpu_server": {
                "status": "online" if gpu_status.get("available") else "offline",
                "latency_ms": gpu_status.get("latency_ms"),
                "services": gpu_status.get("services", {}),
                "error": gpu_status.get("error")
            },
            "llm": {
                "provider": llm_stats.get("primary_provider"),
                "gemini_configured": llm_stats.get("gemini_configured"),
                "openai_configured": llm_stats.get("openai_configured"),
                "free_tier_remaining": llm_stats.get("free_tier_remaining")
            }
        },
        "sessions": session_stats,
        "architecture": "Cost-Optimized (Render Free + Gemini + GPU)"
    }
