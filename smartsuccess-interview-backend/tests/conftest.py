"""
Pytest Configuration and Fixtures
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def client():
    """Create test client for the entire test session"""
    from app.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_env(monkeypatch):
    """Set up mock environment variables"""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000")


@pytest.fixture
def sample_resume():
    """Sample resume text for testing"""
    return """
    JOHN DOE
    AI/ML Engineer
    
    EXPERIENCE:
    - Senior ML Engineer at TechCorp (2020-2024)
      - Built RAG systems using LangChain and ChromaDB
      - Deployed ML models on GCP
    
    SKILLS:
    - Python, FastAPI, LangChain
    - RAG, LLMs, Embeddings
    - GCP, AWS, Docker
    """


@pytest.fixture
def sample_job_description():
    """Sample job description for testing"""
    return """
    AI Engineer - TechStartup
    
    Requirements:
    - 3+ years Python experience
    - Experience with LLM frameworks (LangChain, LlamaIndex)
    - RAG system design and implementation
    - Cloud deployment (GCP/AWS)
    
    Responsibilities:
    - Design and implement AI features
    - Build and optimize RAG pipelines
    - Collaborate with product team
    """
