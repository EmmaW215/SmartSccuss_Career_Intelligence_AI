"""
SmartSuccess.AI Configuration
Cost-Optimized: Render Free ($0) + Gemini (Free tier) + GPU (Self-hosted)

Monthly Cost Breakdown:
├── Render: $0 (free tier)
├── Gemini API: $0-8 (free tier 1500 req/day + overflow)
├── GPU Server: Electricity only (self-hosted 48GB)
└── Total: $0-10/month
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings optimized for minimal cost"""
    
    # ===========================================
    # Environment
    # ===========================================
    environment: str = "production"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", "8000"))
    
    # ===========================================
    # CORS - Allowed Origins
    # ===========================================
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://smart-sccuss-career-intelligence-ai.vercel.app",
        "https://smartsuccess-ai.vercel.app",
        "https://*.vercel.app"
    ]
    
    # ===========================================
    # LLM Configuration - Cost Priority
    # Priority: Gemini 2.0 Flash (FREE) → Gemini 1.5 Flash → GPT-4o-mini
    # ===========================================
    llm_provider: str = "gemini"
    
    # Gemini (Primary - FREE tier: 1500 requests/day)
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    gemini_model_primary: str = "gemini-2.0-flash-exp"
    gemini_model_fallback: str = "gemini-1.5-flash"
    
    # OpenAI (Emergency fallback only)
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_model: str = "gpt-4o-mini"
    
    # LLM Parameters
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    
    # ===========================================
    # GPU Server Configuration (Self-hosted, FREE)
    # ===========================================
    gpu_server_url: Optional[str] = os.getenv("GPU_SERVER_URL")
    gpu_server_timeout: int = 30
    gpu_health_check_interval: int = 60
    
    # ===========================================
    # Voice Configuration
    # ===========================================
    # GPU TTS (Primary - FREE, self-hosted XTTS)
    gpu_tts_model: str = "xtts-v2"
    gpu_tts_voice: str = "professional"
    
    # GPU STT (Primary - FREE, self-hosted Whisper)
    gpu_stt_model: str = "whisper-large-v3"
    
    # Edge-TTS (Emergency fallback - FREE Microsoft)
    edge_tts_voice: str = "en-US-AriaNeural"
    
    # ===========================================
    # Interview Configuration
    # ===========================================
    screening_max_questions: int = 5
    screening_duration_minutes: int = 15
    
    behavioral_max_questions: int = 6
    behavioral_duration_minutes: int = 30
    
    technical_max_questions: int = 8
    technical_duration_minutes: int = 45
    
    customize_max_questions: int = 10
    customize_duration_minutes: int = 45
    
    # ===========================================
    # Session Management (In-memory for Free tier)
    # Note: Sessions lost on restart - acceptable for free tier
    # ===========================================
    session_timeout_minutes: int = 60
    max_concurrent_sessions: int = 50  # RAM limit
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()


# ===========================================
# Cost-Optimized Model Configuration
# ===========================================
COST_OPTIMIZED_CONFIG = {
    "llm": {
        "primary": {
            "provider": "gemini",
            "model": "gemini-2.0-flash-exp",
            "cost_per_1m_tokens": 0,  # Free tier
            "daily_limit": 1500
        },
        "fallback": {
            "provider": "gemini",
            "model": "gemini-1.5-flash",
            "cost_per_1m_tokens": 0.075  # ~$0.075/1M
        },
        "emergency": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "cost_per_1m_tokens": 0.15
        }
    },
    "stt": {
        "primary": {
            "provider": "gpu",
            "model": "whisper-large-v3",
            "cost": 0  # Self-hosted
        },
        "fallback": {
            "provider": "gpu",
            "model": "whisper-base",
            "cost": 0
        }
    },
    "tts": {
        "primary": {
            "provider": "gpu",
            "model": "xtts-v2",
            "cost": 0  # Self-hosted, human-like
        },
        "fallback": {
            "provider": "gpu",
            "model": "coqui-tts",
            "cost": 0
        },
        "emergency": {
            "provider": "edge-tts",
            "model": "en-US-AriaNeural",
            "cost": 0  # Microsoft Edge TTS - FREE
        }
    }
}


# Interview configurations
INTERVIEW_CONFIGS = {
    "screening": {
        "max_questions": 5,
        "duration_minutes": 15,
        "question_types": ["introduction", "motivation", "basic_fit"],
        "follow_up_limit": 1
    },
    "behavioral": {
        "max_questions": 6,
        "duration_minutes": 30,
        "question_types": ["teamwork", "leadership", "challenge", "conflict"],
        "follow_up_limit": 2,
        "use_star_method": True
    },
    "technical": {
        "max_questions": 8,
        "duration_minutes": 45,
        "question_types": ["system_design", "coding", "architecture", "debugging"],
        "follow_up_limit": 2
    },
    "customize": {
        "max_questions": 10,
        "duration_minutes": 45,
        "screening_count": 3,
        "behavioral_count": 3,
        "technical_count": 4,
        "follow_up_limit": 2
    }
}
