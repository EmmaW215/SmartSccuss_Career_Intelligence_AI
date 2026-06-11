"""
Phase 2 Agent Tools — Step D evidence collector

Runs a scripted 3-round screening interview through the agent and saves
each round's tool_call_log as a JSON evidence file (the PRD's "3 份真实
工具调用日志样本").

Modes (auto-selected):
- real_llm:       OPENAI_API_KEY present → real OpenAI tool-calling rounds
                  (~$0.05 total). This is the resume-grade evidence.
- scripted_mock:  no key → deterministic scripted LLM. Files are clearly
                  labeled "scripted_mock" so they are never mistaken for
                  real-LLM evidence.

Usage (from smartsuccess-interview-backend/):
    python scripts/collect_tool_call_logs.py [output_dir]
Default output: docs/phase2_evidence/
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.interviewer_agent import AgentInterviewer, write_tool_call_log
from app.agent.scripted_chat import ScriptedChat, standard_round_script

ROUNDS = [
    {
        "question": "Tell me about yourself.",
        "answer": (
            "I'm a machine learning engineer with five years of Python "
            "experience. At TechCorp I designed a RAG question-answering "
            "platform with LangChain and ChromaDB, deployed it on GCP Cloud "
            "Run, and reduced inference cost per query by 30%."
        ),
        "scripted_next": "Why are you interested in this role?",
    },
    {
        "question": "Why are you interested in this role?",
        "answer": (
            "This role combines RAG system design with production ownership, "
            "which matches what I did when I scaled our prototype to 50k "
            "daily queries. I also want to work closer to the product side, "
            "and your job description emphasizes exactly that collaboration."
        ),
        "scripted_next": "What are your greatest strengths?",
    },
    {
        "question": "What are your greatest strengths?",
        "answer": (
            "My biggest strength is turning ambiguous requirements into "
            "shipped systems: I wrote the design doc, built the evaluation "
            "harness, and drove the LangChain to direct-API migration that "
            "cut our p95 latency by 40%. I'm also a patient mentor — two of "
            "my mentees were promoted last year."
        ),
        "scripted_next": "Where do you see yourself in five years?",
    },
]


async def real_llm_generate(prompt, system_prompt=None, **kwargs):
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


async def main(output_dir: str) -> None:
    key = os.getenv("OPENAI_API_KEY", "")
    real_mode = bool(key) and not key.startswith("test")
    mode = "real_llm" if real_mode else "scripted_mock"
    print(f"Collecting 3 tool_call_log samples in mode: {mode}")
    print(f"Output: {output_dir}\n")

    session_id = f"step_d_staging_{mode}"
    context = {
        "session_id": session_id,
        "interview_type": "screening",
        "resume_text": "ML engineer; Python, LangChain, ChromaDB, GCP.",
        "job_description": "AI Engineer building RAG pipelines on GCP.",
        "questions_asked": [ROUNDS[0]["question"]],
        "current_question_index": 1,
    }

    for i, round_spec in enumerate(ROUNDS, start=1):
        if real_mode:
            agent = AgentInterviewer(llm_generate=real_llm_generate)
        else:
            agent = AgentInterviewer(
                chat_fn=ScriptedChat(
                    turns=standard_round_script(
                        round_spec["question"],
                        round_spec["answer"],
                        round_spec["scripted_next"],
                    )
                )
            )

        result = await agent.run_round(
            context, round_spec["question"], round_spec["answer"]
        )
        path = write_tool_call_log(
            result=result,
            session_id=session_id,
            round_index=i,
            user_answer=round_spec["answer"],
            log_dir=output_dir,
            mode=mode,
        )
        score_ok = any(
            r.tool == "score_answer" and r.status == "ok"
            for r in result.tool_call_log
        )
        print(f"Round {i}: {len(result.tool_call_log)} tool calls, "
              f"score_answer={'ok' if score_ok else 'MISSING'}, "
              f"next='{result.next_question[:60]}'")
        print(f"  -> {path}")

        context["questions_asked"].append(result.next_question)
        context["current_question_index"] += 1

    print("\nDone. 3 evidence files written.")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "docs/phase2_evidence"
    asyncio.run(main(out))
