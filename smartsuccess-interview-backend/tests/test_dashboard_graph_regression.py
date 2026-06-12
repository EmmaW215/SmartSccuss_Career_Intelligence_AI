"""
Dashboard regression tests for graph read-only integration.
"""

from app.api.routes import dashboard as dashboard_route
from app.config import settings
from app.services.session_store import InterviewStatus, SessionStore


class TestDashboardGraphRegression:
    def test_dashboard_history_and_stats_sync_from_graph_when_flag_on(
        self, client, monkeypatch
    ):
        monkeypatch.setattr(settings, "use_langgraph_customize", True)
        store = SessionStore()
        client.app.state.session_store = store

        session = store.create_session(
            user_id="dash_user_001",
            interview_type="customize",
            questions=[{"question": "Q1"}, {"question": "Q2"}, {"question": "Q3"}],
            voice_enabled=False,
        )
        store.update_session(session.session_id, status=InterviewStatus.IN_PROGRESS)

        async def _fake_read_state(session_id: str):
            assert session_id == session.session_id
            return {
                "current_question_index": 3,
                "is_complete": True,
                "last_evaluation": {
                    "hint": "Great structured answer.",
                    "quality": "good",
                },
            }

        monkeypatch.setattr(
            dashboard_route.GraphCheckpointStateAccessor,
            "read_customize_state",
            _fake_read_state,
        )

        history_resp = client.get(f"/api/dashboard/history/{session.user_id}")
        assert history_resp.status_code == 200
        history = history_resp.json()
        assert history["total_interviews"] >= 1
        first = history["interviews"][0]
        assert first["interview_type"] == "customize"
        assert first["status"] == "completed"
        assert first["questions_answered"] >= 3

        stats_resp = client.get(f"/api/dashboard/stats/{session.user_id}")
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert stats["completed_interviews"] >= 1
        assert stats["by_type"]["customize"]["completed"] >= 1

    def test_dashboard_flag_off_uses_legacy_session_state(self, client, monkeypatch):
        monkeypatch.setattr(settings, "use_langgraph_customize", False)
        store = SessionStore()
        client.app.state.session_store = store

        session = store.create_session(
            user_id="dash_user_legacy",
            interview_type="customize",
            questions=[{"question": "Q1"}, {"question": "Q2"}],
            voice_enabled=False,
        )
        store.update_session(
            session.session_id,
            status=InterviewStatus.IN_PROGRESS,
            current_question_index=1,
        )

        async def _unexpected_read_state(session_id: str):
            raise AssertionError("Graph accessor should not be called when flag is off")

        monkeypatch.setattr(
            dashboard_route.GraphCheckpointStateAccessor,
            "read_customize_state",
            _unexpected_read_state,
        )

        history_resp = client.get(f"/api/dashboard/history/{session.user_id}")
        assert history_resp.status_code == 200
        history = history_resp.json()
        first = history["interviews"][0]
        assert first["status"] == "in_progress"
        assert first["questions_answered"] == 1

        stats_resp = client.get(f"/api/dashboard/stats/{session.user_id}")
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert stats["completed_interviews"] == 0
        assert stats["in_progress"] >= 1

    def test_dashboard_feedback_and_report_sync_from_graph_when_flag_on(
        self, client, monkeypatch
    ):
        monkeypatch.setattr(settings, "use_langgraph_customize", True)
        store = SessionStore()
        client.app.state.session_store = store

        session = store.create_session(
            user_id="dash_user_feedback",
            interview_type="customize",
            questions=[{"question": "Q1"}, {"question": "Q2"}, {"question": "Q3"}],
            voice_enabled=False,
        )
        store.update_session(session.session_id, status=InterviewStatus.IN_PROGRESS)

        async def _fake_read_state(session_id: str):
            assert session_id == session.session_id
            return {
                "current_question_index": 2,
                "is_complete": True,
                "last_evaluation": {
                    "hint": "Strong answer with clear outcomes.",
                    "quality": "good",
                },
            }

        monkeypatch.setattr(
            dashboard_route.GraphCheckpointStateAccessor,
            "read_customize_state",
            _fake_read_state,
        )

        feedback_resp = client.get(f"/api/dashboard/session/{session.session_id}/feedback")
        assert feedback_resp.status_code == 200
        feedback = feedback_resp.json()
        assert feedback["status"] == "completed"
        assert feedback["questions_answered"] == 2
        assert feedback["estimated_score"]["good_responses"] >= 1

        report_resp = client.get(f"/api/dashboard/session/{session.session_id}/report")
        assert report_resp.status_code == 200
        report = report_resp.json()
        assert report["session_id"] == session.session_id
        assert report["interview_type"] == "customize"
        assert report["questions_answered"] == 2
        assert report["total_questions"] == 3
        assert report["feedback_analysis"]["good_responses"] >= 1

    def test_dashboard_feedback_and_report_flag_off_keep_legacy_behavior(
        self, client, monkeypatch
    ):
        monkeypatch.setattr(settings, "use_langgraph_customize", False)
        store = SessionStore()
        client.app.state.session_store = store

        session = store.create_session(
            user_id="dash_user_feedback_legacy",
            interview_type="customize",
            questions=[{"question": "Q1"}, {"question": "Q2"}],
            voice_enabled=False,
        )
        store.update_session(
            session.session_id,
            status=InterviewStatus.IN_PROGRESS,
            current_question_index=1,
        )

        async def _unexpected_read_state(session_id: str):
            raise AssertionError("Graph accessor should not be called when flag is off")

        monkeypatch.setattr(
            dashboard_route.GraphCheckpointStateAccessor,
            "read_customize_state",
            _unexpected_read_state,
        )

        feedback_resp = client.get(f"/api/dashboard/session/{session.session_id}/feedback")
        assert feedback_resp.status_code == 200
        feedback = feedback_resp.json()
        assert feedback["status"] == "in_progress"
        assert feedback["questions_answered"] == 1

        report_resp = client.get(f"/api/dashboard/session/{session.session_id}/report")
        assert report_resp.status_code == 400

    def test_dashboard_graph_overlay_is_read_only_no_session_store_mutation(
        self, client, monkeypatch
    ):
        monkeypatch.setattr(settings, "use_langgraph_customize", True)
        store = SessionStore()
        client.app.state.session_store = store

        session = store.create_session(
            user_id="dash_user_read_only",
            interview_type="customize",
            questions=[{"question": "Q1"}, {"question": "Q2"}],
            voice_enabled=False,
        )
        store.update_session(
            session.session_id,
            status=InterviewStatus.IN_PROGRESS,
            current_question_index=0,
            feedback_hints=[],
        )

        async def _fake_read_state(session_id: str):
            assert session_id == session.session_id
            return {
                "current_question_index": 2,
                "is_complete": True,
                "last_evaluation": {
                    "hint": "Graph-only hint.",
                    "quality": "good",
                },
            }

        monkeypatch.setattr(
            dashboard_route.GraphCheckpointStateAccessor,
            "read_customize_state",
            _fake_read_state,
        )

        history_resp = client.get(f"/api/dashboard/history/{session.user_id}")
        assert history_resp.status_code == 200
        history = history_resp.json()
        first = history["interviews"][0]
        assert first["status"] == "completed"
        assert first["questions_answered"] == 2

        stored_after = store.get_session(session.session_id)
        assert stored_after is not None
        assert stored_after.status == InterviewStatus.IN_PROGRESS
        assert stored_after.current_question_index == 0
        assert stored_after.completed_at is None
        assert stored_after.feedback_hints == []
