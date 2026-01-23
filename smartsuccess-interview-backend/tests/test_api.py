"""
Basic Tests for SmartSuccess Interview Backend
"""

import pytest


# Test health endpoints
class TestHealth:
    """Test health check endpoints"""
    
    def test_health_check(self, client):
        """Test main health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_readiness_check(self, client):
        """Test readiness endpoint"""
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["ready"] == True
    
    def test_liveness_check(self, client):
        """Test liveness endpoint"""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["alive"] == True


# Test screening interview
class TestScreeningInterview:
    """Test screening interview endpoints"""
    
    def test_start_screening_session(self, client):
        """Test starting a screening session"""
        response = client.post(
            "/api/interview/screening/start",
            json={"user_id": "test_user_001"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["interview_type"] == "screening"
        assert "greeting" in data
    
    def test_get_screening_questions(self, client):
        """Test getting screening questions"""
        response = client.get("/api/interview/screening/questions")
        assert response.status_code == 200
        data = response.json()
        assert data["interview_type"] == "screening"
        assert "questions" in data


# Test behavioral interview
class TestBehavioralInterview:
    """Test behavioral interview endpoints"""
    
    def test_start_behavioral_session(self, client):
        """Test starting a behavioral session"""
        response = client.post(
            "/api/interview/behavioral/start",
            json={"user_id": "test_user_002"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["interview_type"] == "behavioral"
    
    def test_get_star_guide(self, client):
        """Test getting STAR method guide"""
        response = client.get("/api/interview/behavioral/star-guide")
        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "STAR"
        assert "components" in data


# Test technical interview
class TestTechnicalInterview:
    """Test technical interview endpoints"""
    
    def test_start_technical_session(self, client):
        """Test starting a technical session"""
        response = client.post(
            "/api/interview/technical/start",
            json={"user_id": "test_user_003"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["interview_type"] == "technical"
    
    def test_get_technical_domains(self, client):
        """Test getting technical domains"""
        response = client.get("/api/interview/technical/domains")
        assert response.status_code == 200
        data = response.json()
        assert "domains" in data


# Test voice endpoints
class TestVoice:
    """Test voice endpoints"""
    
    def test_get_voices(self, client):
        """Test getting available voices"""
        response = client.get("/api/voice/voices")
        assert response.status_code == 200
        data = response.json()
        assert "voices" in data
        assert len(data["voices"]) > 0
    
    def test_voice_status(self, client):
        """Test voice service status"""
        response = client.get("/api/voice/status")
        assert response.status_code == 200
        data = response.json()
        assert "available" in data
