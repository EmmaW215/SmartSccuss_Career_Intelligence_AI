"""
Contract tests for customize interview graph path.

Ensures API response shape remains frontend-compatible when
use_langgraph_customize=True.
"""

from app.services.session_store import SessionStore
from app.api.routes import customize as customize_route
from app.config import settings


class _FakeGpuClient:
    async def check_health(self, force: bool = False):
        return {
            "available": True,
            "services": {"whisper": True, "tts": True, "rag": True},
            "latency_ms": 5,
        }


class _FakeConversationEngine:
    def __init__(self):
        self._contexts = {}

    def create_context(self, **kwargs):
        ctx = {"session_id": kwargs["session_id"]}
        self._contexts[kwargs["session_id"]] = ctx
        return ctx

    def get_context(self, session_id: str):
        return self._contexts.get(session_id)

    async def generate_greeting(self, context, user_name=None):
        return f"Legacy greeting for {user_name or 'candidate'}"

    async def process_response(self, context, user_response: str, next_question: str):
        return {
            "ai_response": f"Legacy response: {next_question}",
            "tone": "friendly",
            "feedback_hint": {"hint": "Legacy hint", "quality": "good"},
            "question_index": 1,
            "is_complete": False,
            "should_end": False,
        }

    async def generate_closing(self, context):
        return "Legacy closing."


class TestCustomizeGraphContract:
    def test_customize_start_contract_graph_path(self, client, monkeypatch):
        monkeypatch.setattr(settings, "use_langgraph_customize", True)
        client.app.state.session_store = SessionStore()
        monkeypatch.setattr(customize_route, "get_gpu_client", lambda: _FakeGpuClient())

        async def _fake_start_customize_with_graph(**kwargs):
            return {
                "ai_response": "Graph greeting contract",
                "is_complete": False,
                "current_question_index": 0,
                "next_action": "next_question",
                "last_evaluation": None,
            }

        monkeypatch.setattr(
            customize_route,
            "start_customize_with_graph",
            _fake_start_customize_with_graph,
        )

        response = client.post(
            "/api/interview/customize/start",
            json={"user_id": "graph_user_001", "user_name": "Emma", "voice_enabled": True},
        )

        assert response.status_code == 200
        data = response.json()
        required_keys = {
            "session_id",
            "greeting",
            "total_questions",
            "voice_enabled",
            "interview_type",
            "profile_used",
            "gpu_available",
        }
        assert required_keys.issubset(data.keys())
        assert data["interview_type"] == "customize"
        assert isinstance(data["session_id"], str) and len(data["session_id"]) > 0
        assert isinstance(data["greeting"], str) and len(data["greeting"]) > 0
        assert isinstance(data["total_questions"], int)
        assert isinstance(data["gpu_available"], bool)

    def test_customize_respond_contract_graph_path_in_progress(self, client, monkeypatch):
        monkeypatch.setattr(settings, "use_langgraph_customize", True)
        client.app.state.session_store = SessionStore()
        monkeypatch.setattr(customize_route, "get_gpu_client", lambda: _FakeGpuClient())

        async def _fake_start_customize_with_graph(**kwargs):
            return {
                "ai_response": "Graph greeting contract",
                "is_complete": False,
                "current_question_index": 0,
                "next_action": "next_question",
                "last_evaluation": None,
            }

        async def _fake_respond_customize_with_graph(**kwargs):
            return {
                "ai_response": "Thanks. Next question: Tell me about your system design approach.",
                "is_complete": False,
                "current_question_index": 1,
                "next_action": "next_question",
                "last_evaluation": {
                    "hint": "Add more concrete examples.",
                    "quality": "fair",
                },
            }

        monkeypatch.setattr(
            customize_route,
            "start_customize_with_graph",
            _fake_start_customize_with_graph,
        )
        monkeypatch.setattr(
            customize_route,
            "respond_customize_with_graph",
            _fake_respond_customize_with_graph,
        )

        start = client.post(
            "/api/interview/customize/start",
            json={"user_id": "graph_user_002", "user_name": "Emma", "voice_enabled": False},
        )
        assert start.status_code == 200
        session_id = start.json()["session_id"]

        response = client.post(
            "/api/interview/customize/respond",
            json={"session_id": session_id, "user_response": "I usually begin with clear boundaries and requirements."},
        )

        assert response.status_code == 200
        data = response.json()
        required_keys = {
            "ai_response",
            "tone",
            "feedback_hint",
            "current_question",
            "total_questions",
            "current_category",
            "is_complete",
            "session_id",
        }
        assert required_keys.issubset(data.keys())
        assert data["is_complete"] is False
        assert data["session_id"] == session_id
        assert isinstance(data["current_question"], int)
        assert isinstance(data["feedback_hint"], dict)
        assert data["feedback_hint"]["quality"] in {"good", "fair", "needs_improvement"}

    def test_customize_respond_contract_graph_path_complete(self, client, monkeypatch):
        monkeypatch.setattr(settings, "use_langgraph_customize", True)
        client.app.state.session_store = SessionStore()
        monkeypatch.setattr(customize_route, "get_gpu_client", lambda: _FakeGpuClient())

        async def _fake_start_customize_with_graph(**kwargs):
            return {
                "ai_response": "Graph greeting contract",
                "is_complete": False,
                "current_question_index": 0,
                "next_action": "next_question",
                "last_evaluation": None,
            }

        async def _fake_respond_customize_with_graph(**kwargs):
            return {
                "ai_response": "Thanks for completing the interview.",
                "is_complete": True,
                "current_question_index": 4,
                "next_action": "closing",
                "last_evaluation": {
                    "hint": "Good overall clarity.",
                    "quality": "good",
                },
            }

        monkeypatch.setattr(
            customize_route,
            "start_customize_with_graph",
            _fake_start_customize_with_graph,
        )
        monkeypatch.setattr(
            customize_route,
            "respond_customize_with_graph",
            _fake_respond_customize_with_graph,
        )

        start = client.post(
            "/api/interview/customize/start",
            json={"user_id": "graph_user_003", "user_name": "Emma", "voice_enabled": False},
        )
        assert start.status_code == 200
        session_id = start.json()["session_id"]

        response = client.post(
            "/api/interview/customize/respond",
            json={"session_id": session_id, "user_response": "end"},
        )

        assert response.status_code == 200
        data = response.json()
        required_keys = {"ai_response", "is_complete", "feedback_hint", "session_id"}
        assert required_keys.issubset(data.keys())
        assert data["is_complete"] is True
        assert data["session_id"] == session_id

    def test_customize_flag_off_falls_back_to_legacy_path(self, client, monkeypatch):
        monkeypatch.setattr(settings, "use_langgraph_customize", False)
        client.app.state.session_store = SessionStore()
        monkeypatch.setattr(customize_route, "get_gpu_client", lambda: _FakeGpuClient())

        fake_engine = _FakeConversationEngine()
        monkeypatch.setattr(customize_route, "get_conversation_engine", lambda: fake_engine)

        async def _unexpected_graph_start(**kwargs):
            raise AssertionError("Graph start should not be called when flag is off")

        async def _unexpected_graph_respond(**kwargs):
            raise AssertionError("Graph respond should not be called when flag is off")

        monkeypatch.setattr(
            customize_route,
            "start_customize_with_graph",
            _unexpected_graph_start,
        )
        monkeypatch.setattr(
            customize_route,
            "respond_customize_with_graph",
            _unexpected_graph_respond,
        )

        start = client.post(
            "/api/interview/customize/start",
            json={"user_id": "legacy_user_001", "user_name": "Emma", "voice_enabled": False},
        )
        assert start.status_code == 200
        start_data = start.json()
        assert start_data["interview_type"] == "customize"
        assert "Legacy greeting" in start_data["greeting"]
        session_id = start_data["session_id"]

        response = client.post(
            "/api/interview/customize/respond",
            json={"session_id": session_id, "user_response": "I led a migration project."},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_complete"] is False
        assert "Legacy response:" in data["ai_response"]
        assert data["tone"] == "friendly"
        assert data["feedback_hint"]["quality"] == "good"
        assert data["session_id"] == session_id
