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
    
    # Embedding Configuration
    embedding_provider: str = "openai"  # openai, xai
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    
    # LLM Configuration
    llm_provider: str = "openai"  # openai, groq, anthropic
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1024
    
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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Convenience function to get settings
settings = get_settings()
