"""
Phase 2 Agent Tools — Real-LLM integration tests (Step C acceptance)

PRD 02_PHASE2_AGENT_TOOLS.md requires three @pytest.mark.llm scenarios:
1. Scripted single round against the REAL interviewer agent (real OpenAI)
2. "tool error → agent keeps asking" end-to-end self-healing
3. Statistical assertion: every round logs score_answer + decision chain

These are MANUAL tests — excluded by default (pytest.ini: -m "not llm"),
cost roughly $0.05 per run, and require a real OPENAI_API_KEY:

    pytest -m llm tests/test_llm_integration.py -v
"""

import os

import pytest

from app.agent.interviewer_agent import AgentInterviewer
from app.agent.tools import AgentToolkit

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY", "").startswith("test"),
        reason="Real OPENAI_API_KEY required (manual run, ~$0.05)",
    ),
]

QUESTION = "Tell me about yourself."
ANSWER = (
    "I'm a machine learning engineer with five years of Python experience. "
    "At TechCorp I designed a RAG question-answering platform with LangChain "
    "and ChromaDB, deployed it on GCP Cloud Run, and reduced our inference "
    "cost per query by 30% while raising answer accuracy to 92%."
)


def make_context():
    return {
        "session_id": "llm_integration_test",
        "interview_type": "screening",
        "resume_text": "ML engineer; Python, LangChain, ChromaDB, GCP.",
        "job_description": "AI Engineer building RAG pipelines on GCP.",
        "questions_asked": [QUESTION],
        "current_question_index": 1,
    }


async def real_llm_generate(prompt, system_prompt=None, **kwargs):
    """Direct OpenAI generate for score_answer (bypasses fallback chain)."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI()
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    response = await client.chat.completions.create(
        model="gpt-4o-mini", messages=messages, temperature=0.2, max_tokens=512
    )
    return response.choices[0].message.content


# ================================================================
# PRD llm test 1: scripted real-LLM interviewer round
# ================================================================

async def test_real_llm_scripted_round():
    """One full real-LLM round: answer in → tools used → next question out."""
    agent = AgentInterviewer(llm_generate=real_llm_generate)
    result = await agent.run_round(make_context(), QUESTION, ANSWER)

    assert result.next_question.strip(), "agent must produce a next question"
    assert result.next_question.strip() != QUESTION
    assert not result.used_fallback, (
        "real LLM round should not need the bank fallback"
    )
    assert result.tool_call_log, "real round must log its tool calls"
    assert result.evaluation.get("ok") is True
    assert result.evaluation.get("overall", 0) >= 1


# ================================================================
# PRD llm test 2: tool error → agent continues asking (E2E)
# ================================================================

async def test_real_llm_self_heals_after_tool_error(monkeypatch):
    """Break search_question_bank; the real agent must absorb the error
    payload and still continue the interview with a next question."""
    def broken_search(*args, **kwargs):
        raise ConnectionError("question bank backend unreachable")

    monkeypatch.setattr(AgentToolkit, "search_question_bank", broken_search)

    agent = AgentInterviewer(llm_generate=real_llm_generate)
    result = await agent.run_round(make_context(), QUESTION, ANSWER)

    assert result.next_question.strip(), (
        "agent must keep asking after a tool error"
    )
    # If the model attempted the broken tool, the error must be in the log
    errors = [r for r in result.tool_call_log if r.status == "error"]
    if errors:
        assert result.healed_errors == len(errors)
        assert all(r.tool == "search_question_bank" for r in errors)
    # Scoring must still have happened (organically or enforced)
    assert any(
        r.tool == "score_answer" and r.status == "ok"
        for r in result.tool_call_log
    )


# ================================================================
# PRD llm test 3: every round logs score_answer + decision chain
# ================================================================

async def test_real_llm_log_quality_statistics():
    """Run two consecutive real rounds and assert tool_call_log quality:
    >=1 successful score_answer and non-empty decisions per round."""
    agent = AgentInterviewer(llm_generate=real_llm_generate)
    context = make_context()
    answers = [
        ANSWER,
        "I'm drawn to this role because it combines RAG system design with "
        "production ownership, which is exactly what I did at TechCorp when "
        "I took our prototype to 50k daily queries.",
    ]

    current_question = QUESTION
    for round_index, answer in enumerate(answers, start=1):
        result = await agent.run_round(context, current_question, answer)

        scores = [
            r for r in result.tool_call_log
            if r.tool == "score_answer" and r.status == "ok"
        ]
        assert scores, f"round {round_index}: no successful score_answer"
        assert result.decision_chain, f"round {round_index}: empty decision chain"
        for record in result.tool_call_log:
            assert record.decision.strip(), (
                f"round {round_index}: {record.tool} missing decision"
            )

        context["questions_asked"].append(result.next_question)
        context["current_question_index"] += 1
        current_question = result.next_question
