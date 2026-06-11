"""
Phase 2 Agent Tools — Flag regression tests (Step D baseline)

Proves the PRD backward-compatibility guarantee:
- USE_AGENT_TOOLS=false (default): Phase 1 interview flow is byte-for-byte
  the same code path; the agent is never engaged.
- USE_AGENT_TOOLS=true: rounds run through the agent, sessions carry the
  tool_call_log, and evidence files are written.
- Agent failure with the flag on degrades gracefully to the Phase 1 flow.
"""

import uuid

import pytest

from app.config import settings
from app.interview.screening_interview import ScreeningInterviewService
from app.models import InterviewPhase
from app.agent.interviewer_agent import AgentInterviewer
from app.agent.scripted_chat import ScriptedChat, standard_round_script

ANSWER = (
    "I have five years of experience building machine learning systems in "
    "Python, most recently leading a RAG platform migration at TechCorp."
)
NEXT_QUESTION = "Why are you interested in this role?"


@pytest.fixture
async def screening_session():
    """A screening service + in-progress session with Phase 1 LLM stubs."""
    service = ScreeningInterviewService()

    async def stub_evaluate(session, response):
        return {"overall_score": 4.0, "stub": "phase1"}

    async def stub_follow_up(session, evaluation):
        return None

    async def stub_next_question(session):
        return "Phase 1 next question?"

    service._evaluate_response = stub_evaluate
    service._check_follow_up = stub_follow_up
    service._get_next_question = stub_next_question

    session = await service.create_session(user_id=f"reg_{uuid.uuid4().hex[:8]}")
    session.phase = InterviewPhase.IN_PROGRESS
    session.questions_asked.append("Tell me about yourself.")
    session.current_question_index = 1
    service._persist_session(session)
    return service, session


class TestFlagOff:

    def test_default_flags_are_off(self):
        """PRD: agent tools and MCP must default to disabled."""
        from app.config import Settings
        defaults = Settings(_env_file=None)
        assert defaults.use_agent_tools is False
        assert defaults.use_mcp_tools is False

    async def test_phase1_flow_never_touches_agent(
        self, screening_session, monkeypatch
    ):
        """With the flag off, AgentInterviewer.run_round must not run."""
        service, session = screening_session
        monkeypatch.setattr(settings, "use_agent_tools", False)

        async def forbidden(*args, **kwargs):
            raise AssertionError("Agent engaged while USE_AGENT_TOOLS=false")

        monkeypatch.setattr(AgentInterviewer, "run_round", forbidden)

        response = await service.process_message(session.session_id, ANSWER)
        assert response.type == "question"
        assert response.message == "Phase 1 next question?"
        assert response.evaluation == {"overall_score": 4.0, "stub": "phase1"}
        # Phase 1 responses carry no agent evidence fields
        assert "tool_call_log" not in session.responses[-1]


class TestFlagOn:

    async def test_agent_round_records_tool_call_log(
        self, screening_session, monkeypatch, tmp_path
    ):
        service, session = screening_session
        monkeypatch.setattr(settings, "use_agent_tools", True)
        monkeypatch.setattr(settings, "tool_call_log_dir", str(tmp_path))

        service._agent_chat_override = ScriptedChat(
            turns=standard_round_script(
                "Tell me about yourself.", ANSWER, NEXT_QUESTION
            )
        )

        response = await service.process_message(session.session_id, ANSWER)

        assert response.type == "question"
        assert response.message == NEXT_QUESTION
        recorded = session.responses[-1]
        assert recorded["tool_call_log"], "agent round must persist its log"
        assert recorded["decision_chain"]
        assert any(
            r["tool"] == "score_answer" and r["status"] == "ok"
            for r in recorded["tool_call_log"]
        )
        # Step D evidence file written
        log_files = list(tmp_path.glob("*_round*.json"))
        assert len(log_files) == 1

    async def test_agent_failure_falls_back_to_phase1(
        self, screening_session, monkeypatch
    ):
        """If the agent layer itself crashes, the round still completes
        through the unchanged Phase 1 flow."""
        service, session = screening_session
        monkeypatch.setattr(settings, "use_agent_tools", True)

        async def crashing_round(*args, **kwargs):
            raise RuntimeError("agent layer exploded")

        monkeypatch.setattr(AgentInterviewer, "run_round", crashing_round)

        response = await service.process_message(session.session_id, ANSWER)
        assert response.type == "question"
        assert response.message == "Phase 1 next question?"

    async def test_end_keywords_bypass_agent(self, screening_session, monkeypatch):
        """'stop' style messages complete the interview without an agent round."""
        service, session = screening_session
        monkeypatch.setattr(settings, "use_agent_tools", True)

        async def forbidden(*args, **kwargs):
            raise AssertionError("Agent should not run for end keywords")

        monkeypatch.setattr(AgentInterviewer, "run_round", forbidden)

        async def stub_summary(session):
            from app.models import SessionSummary, InterviewType
            return SessionSummary(
                session_id=session.session_id,
                interview_type=InterviewType.SCREENING,
                total_questions=1, total_responses=1,
                duration_minutes=1.0, overall_score=4.0,
            )

        async def stub_completion(session):
            return "Thanks, the interview is complete."

        service._generate_summary = stub_summary
        service._get_completion_message = stub_completion

        response = await service.process_message(
            session.session_id, "I am done, please stop the interview now."
        )
        assert response.type == "completion"
