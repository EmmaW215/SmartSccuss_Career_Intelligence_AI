"""
Health Check Route
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SmartSuccess Interview Backend",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/ready")
async def readiness_check():
    """Readiness check for load balancers"""
    return {"ready": True}


@router.get("/health/live")
async def liveness_check():
    """Liveness check for orchestrators"""
    return {"alive": True}
