"""
Configuration Management for SmartSuccess Interview Backend
Uses Pydantic Settings for type-safe environment variable handling
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"
    
    # AI Service Keys
    openai_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None  # Phase 2: Gemini API key
    
    # Phase 2: Cost Optimization Mode (default: False - keep existing behavior)
    cost_optimized_mode: bool = False  # True = use Gemini + GPU, False = use OpenAI (default)
    
    # Embedding Configuration
    embedding_provider: str = "openai"  # openai, xai
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    
    # LLM Configuration
    llm_provider: str = "openai"  # openai, groq, anthropic, gemini, auto
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    
    # Phase 2: Gemini Configuration (when cost_optimized_mode=True)
    gemini_model_primary: str = "gemini-2.0-flash-exp"
    gemini_model_fallback: str = "gemini-1.5-flash"
    
    # Phase 2: GPU Server Configuration (optional)
    gpu_server_url: Optional[str] = None
    gpu_server_timeout: int = 30
    gpu_health_check_interval: int = 60  # Health check cache TTL in seconds
    use_gpu_voice: bool = False  # True = GPU STT/TTS, False = OpenAI (default)
    
    # Phase 2: Conversation Engine (natural conversation mode)
    use_conversation_engine: bool = True  # Enable natural conversation style
    
    # Phase 2: Edge-TTS Fallback (free Microsoft TTS)
    edge_tts_voice: str = "en-US-AriaNeural"
    
    # Phase 2: Session Management (for customize/dashboard features)
    session_timeout_minutes: int = 60
    max_concurrent_sessions: int = 50
    
    # Voice Configuration
    whisper_model: str = "whisper-1"
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"
    
    # Interview Configuration
    screening_max_questions: int = 5
    screening_duration_minutes: int = 15
    behavioral_max_questions: int = 6
    behavioral_duration_minutes: int = 30
    technical_max_questions: int = 8
    technical_duration_minutes: int = 45
    
    # Data paths
    data_dir: str = "data"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Phase 2: Cost-Optimized Model Configuration (optional)
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
    }
}


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Convenience function to get settings
settings = get_settings()
