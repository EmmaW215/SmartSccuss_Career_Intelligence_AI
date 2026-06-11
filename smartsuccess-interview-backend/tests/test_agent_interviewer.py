"""
Phase 2 Agent Tools — Agent loop tests (offline, scripted LLM)

Covers the PRD 02_PHASE2_AGENT_TOOLS.md Step C acceptance scenarios in
their offline form (real-LLM variants live in test_llm_integration.py):

- "tool 报错 → agent 继续提问" end-to-end self-healing loop
- "每轮至少含 score_answer + 决策链" tool_call_log quality statistics
"""

import json

import pytest

from app.agent.interviewer_agent import AgentInterviewer
from app.agent.scripted_chat import (
    ScriptedChat,
    final_turn,
    standard_round_script,
    tool_call_turn,
)
from app.agent.tools import AgentToolkit

QUESTION = "Tell me about yourself."
ANSWER = (
    "I'm an ML engineer with 5 years of Python experience. At TechCorp I "
    "built RAG pipelines with LangChain and deployed them on GCP, cutting "
    "inference costs by 30%."
)
NEXT_QUESTION = "Why are you interested in this role?"


def make_context(asked=None):
    return {
        "session_id": "screening_test_0001",
        "interview_type": "screening",
        "resume_text": "ML engineer, Python, LangChain, GCP",
        "job_description": "AI Engineer role, RAG systems",
        "questions_asked": asked or [QUESTION],
        "current_question_index": 1,
    }


async def run_scripted_round(turns, **agent_kwargs):
    chat = ScriptedChat(turns=turns)
    agent = AgentInterviewer(chat_fn=chat, **agent_kwargs)
    result = await agent.run_round(make_context(), QUESTION, ANSWER)
    return result, chat


# ================================================================
# Happy path
# ================================================================

class TestHappyPath:

    async def test_standard_round_produces_question_and_log(self):
        result, chat = await run_scripted_round(
            standard_round_script(QUESTION, ANSWER, NEXT_QUESTION)
        )
        assert result.next_question == NEXT_QUESTION
        assert not result.used_fallback
        assert not result.score_enforced
        assert result.healed_errors == 0
        # score_answer + search_question_bank + save_interview_note
        assert [r.tool for r in result.tool_call_log] == [
            "score_answer", "search_question_bank", "save_interview_note",
        ]
        assert all(r.status == "ok" for r in result.tool_call_log)
        assert result.evaluation["ok"] is True
        assert result.notes  # save_interview_note persisted

    async def test_tools_offered_to_llm_match_registry(self):
        _, chat = await run_scripted_round(
            standard_round_script(QUESTION, ANSWER, NEXT_QUESTION)
        )
        offered = {t["function"]["name"] for t in chat.calls[0]["tools"]}
        assert offered == {
            "search_question_bank", "score_answer",
            "get_candidate_profile", "save_interview_note",
        }

    async def test_decision_chain_records_assistant_reasoning(self):
        result, _ = await run_scripted_round(
            standard_round_script(QUESTION, ANSWER, NEXT_QUESTION)
        )
        assert len(result.decision_chain) == len(result.tool_call_log)
        assert all(d.strip() for d in result.decision_chain)
        assert "[score_answer]" in result.decision_chain[0]


# ================================================================
# PRD scenario: tool error → agent continues asking (self-healing)
# ================================================================

class TestSelfHealingLoop:

    async def test_tool_error_fed_back_and_round_completes(self, monkeypatch):
        """E2E: search_question_bank explodes mid-round; the agent keeps
        going and still delivers the next question."""
        def broken_search(*args, **kwargs):
            raise ConnectionError("question bank backend unreachable")

        monkeypatch.setattr(AgentToolkit, "search_question_bank", broken_search)

        turns = [
            tool_call_turn([{
                "name": "score_answer",
                "arguments": {"question": QUESTION, "answer": ANSWER,
                              "interview_type": "screening"},
            }]),
            tool_call_turn(
                [{"name": "search_question_bank",
                  "arguments": {"interview_type": "screening"}}],
                content="Looking up the next question.",
            ),
            final_turn(NEXT_QUESTION),
        ]
        result, chat = await run_scripted_round(turns)

        # The error was logged, surfaced to the LLM, and the round finished
        error_records = [r for r in result.tool_call_log if r.status == "error"]
        assert len(error_records) == 1
        assert error_records[0].tool == "search_question_bank"
        assert result.healed_errors == 1
        assert result.next_question == NEXT_QUESTION

        # The LLM saw the error payload as a tool message and continued
        last_call_messages = chat.calls[-1]["messages"]
        tool_messages = [m for m in last_call_messages if m.get("role") == "tool"]
        assert any(
            not json.loads(m["content"]).get("ok") for m in tool_messages
        )

    async def test_chat_failure_still_yields_question_and_score(self):
        """Even a total LLM outage cannot kill the round: fallback question
        from the bank + enforced heuristic scoring."""
        async def dead_chat(messages, tools):
            raise TimeoutError("LLM gateway timeout")

        agent = AgentInterviewer(chat_fn=dead_chat)
        result = await agent.run_round(make_context(), QUESTION, ANSWER)

        assert result.used_fallback
        assert result.next_question  # from question bank
        assert result.next_question != QUESTION  # not a repeat
        assert result.score_enforced
        assert result.evaluation.get("ok") is True

    async def test_max_iterations_triggers_bank_fallback(self):
        """An LLM that loops on tools forever gets cut off and the round
        falls back to a deterministic bank question."""
        looping_turn = lambda: tool_call_turn(
            [{"name": "get_candidate_profile", "arguments": {}}]
        )
        chat = ScriptedChat(turns=[looping_turn() for _ in range(3)])
        agent = AgentInterviewer(chat_fn=chat, max_iterations=3)
        result = await agent.run_round(make_context(), QUESTION, ANSWER)

        assert result.used_fallback
        assert result.next_question
        assert any("[fallback]" in d for d in result.decision_chain)


# ================================================================
# PRD scenario: every round has score_answer + decision chain
# ================================================================

class TestToolCallLogQuality:

    async def test_score_answer_enforced_when_llm_skips_it(self):
        """LLM that goes straight to the next question still gets a
        score_answer entry (enforced) in the log."""
        result, _ = await run_scripted_round([final_turn(NEXT_QUESTION)])

        assert result.score_enforced
        score_records = [
            r for r in result.tool_call_log if r.tool == "score_answer"
        ]
        assert len(score_records) == 1
        assert score_records[0].enforced is True
        assert score_records[0].status == "ok"
        assert result.evaluation["ok"] is True

    async def test_statistics_every_round_has_score_and_decisions(self):
        """Statistical assertion over multiple rounds, including
        misbehaving ones: every round's log contains >=1 successful
        score_answer and a non-empty decision on every record."""
        round_scripts = [
            # Round 1: well-behaved
            standard_round_script(QUESTION, ANSWER, NEXT_QUESTION),
            # Round 2: skips scoring entirely
            [final_turn("What are your greatest strengths?")],
            # Round 3: only consults profile, then answers
            [
                tool_call_turn([{"name": "get_candidate_profile", "arguments": {}}]),
                final_turn("Where do you see yourself in five years?"),
            ],
        ]

        results = []
        for turns in round_scripts:
            result, _ = await run_scripted_round(turns)
            results.append(result)

        for i, result in enumerate(results, start=1):
            successful_scores = [
                r for r in result.tool_call_log
                if r.tool == "score_answer" and r.status == "ok"
            ]
            assert successful_scores, f"round {i} missing score_answer"
            assert result.decision_chain, f"round {i} missing decision chain"
            for record in result.tool_call_log:
                assert record.decision.strip(), (
                    f"round {i} tool {record.tool} has empty decision"
                )
            # Log entries serialize cleanly for the Step D evidence files
            payload = result.to_dict()
            assert json.dumps(payload)  # round-trippable
            assert payload["tool_call_log"][0]["seq"] == 1

    async def test_log_written_to_disk(self, tmp_path):
        from app.agent.interviewer_agent import write_tool_call_log

        result, _ = await run_scripted_round(
            standard_round_script(QUESTION, ANSWER, NEXT_QUESTION)
        )
        path = write_tool_call_log(
            result=result,
            session_id="screening_test_0001",
            round_index=1,
            user_answer=ANSWER,
            log_dir=str(tmp_path),
            mode="scripted_mock",
        )
        saved = json.loads(path.read_text())
        assert saved["session_id"] == "screening_test_0001"
        assert saved["mode"] == "scripted_mock"
        assert saved["tool_call_log"]
        assert saved["decision_chain"]
