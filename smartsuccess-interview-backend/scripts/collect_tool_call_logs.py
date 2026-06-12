"""
Step D evidence collector (PRD 02 §10 step 5 / acceptance criteria 1-2).

Runs scripted interviews with USE_AGENT_TOOLS=true against the real ReAct
interviewer (gpt-4o-mini) and archives each session's tool_call_log as a JSON
sample under PHASE2_PCodingPlace_20260611/evidence/tool_call_logs/.

Usage (from smartsuccess-interview-backend/):
    .venv_test/bin/python scripts/collect_tool_call_logs.py

Requires a real OPENAI_API_KEY in .env. Cost ~= $0.05 per session.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKEND_DIR = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = BACKEND_DIR.parents[1] / "evidence" / "tool_call_logs"

SCENARIOS = [
    {
        "name": "backend_engineer_strong_answers",
        "user_id": "evidence_user_001",
        "user_name": "Sample Candidate A",
        "answers": [
            "I led the migration of our interview platform to LangGraph. I designed the "
            "state schema, added a Postgres checkpointer for session recovery, and "
            "rolled it out behind a feature flag with zero regressions across 37 tests.",
            "The hardest part was checkpoint state compatibility. I wrote a state "
            "accessor layer so the API contract stayed identical, and verified it with "
            "contract tests before flipping the flag in production.",
        ],
    },
    {
        "name": "ml_engineer_vague_then_probed",
        "user_id": "evidence_user_002",
        "user_name": "Sample Candidate B",
        "answers": [
            "I worked on some machine learning models and improved them.",
            "We used a RAG pipeline with embeddings to ground the model in our docs, "
            "and I measured answer relevance before and after with an eval set of 200 "
            "questions, improving accuracy from 71% to 84%.",
        ],
    },
    {
        "name": "agent_autonomy_multi_turn",
        "user_id": "evidence_user_003",
        "user_name": "Sample Candidate C",
        "answers": [
            "I built a multi-agent system where an interviewer agent calls a separate "
            "evaluator agent through a score_answer tool, and every decision is logged "
            "to a tool_call_log audit trail with result digests and timestamps.",
            "For loop safety I capped agent iterations and added a recursion limit, "
            "with a deterministic fallback path so the interview never stalls.",
            "Observability matters because an autonomous agent's routing decisions "
            "must be explainable after the fact, both for debugging and for trust.",
        ],
    },
]


def main() -> None:
    from app.config import settings

    if not (settings.openai_api_key or "").startswith("sk-"):
        raise SystemExit("A real OPENAI_API_KEY is required to collect evidence samples.")

    settings.use_langgraph_customize = True
    settings.use_agent_tools = True
    settings.use_mcp_tools = False
    settings.max_agent_iterations = 4

    from app.api.routes import customize as customize_route

    class _OfflineGpuClient:
        async def check_health(self, force: bool = False):
            return {"available": False, "services": {}, "latency_ms": 0}

    customize_route.get_gpu_client = lambda: _OfflineGpuClient()

    from fastapi.testclient import TestClient

    from app.graph.checkpoint_state_accessor import GraphCheckpointStateAccessor
    from app.main import app
    from app.services.session_store import SessionStore

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    collected = []

    with TestClient(app) as client:
        client.app.state.session_store = SessionStore()
        for index, scenario in enumerate(SCENARIOS, start=1):
            start_resp = client.post(
                "/api/interview/customize/start",
                json={
                    "user_id": scenario["user_id"],
                    "user_name": scenario["user_name"],
                    "voice_enabled": False,
                },
            )
            start_resp.raise_for_status()
            session_id = start_resp.json()["session_id"]

            turns = []
            for answer in scenario["answers"]:
                resp = client.post(
                    "/api/interview/customize/respond",
                    json={"session_id": session_id, "user_response": answer},
                )
                resp.raise_for_status()
                data = resp.json()
                turns.append(
                    {
                        "candidate_answer": answer,
                        "interviewer_response": data.get("ai_response") or data.get("question"),
                        "is_complete": data.get("is_complete", False),
                    }
                )
                if data.get("is_complete"):
                    break

            state = asyncio.new_event_loop().run_until_complete(
                GraphCheckpointStateAccessor.read_customize_state(session_id)
            )
            tool_call_log = list(state.get("tool_call_log", [])) if state else []

            sample = {
                "sample": scenario["name"],
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "model": settings.agent_model,
                "flags": {
                    "USE_LANGGRAPH_CUSTOMIZE": True,
                    "USE_AGENT_TOOLS": True,
                    "USE_MCP_TOOLS": False,
                    "max_agent_iterations": settings.max_agent_iterations,
                },
                "session_id": session_id,
                "turns": turns,
                "autonomous_tool_calls": len(tool_call_log),
                "tools_used": sorted({e.get("tool", "") for e in tool_call_log}),
                "tool_call_log": tool_call_log,
                "evaluations": list(state.get("evaluations", [])) if state else [],
                "final_next_action": state.get("next_action") if state else None,
            }

            out_path = EVIDENCE_DIR / f"sample_{index:02d}_{scenario['name']}.json"
            out_path.write_text(json.dumps(sample, ensure_ascii=False, indent=2, default=str))
            collected.append((out_path, len(tool_call_log), sample["tools_used"]))
            print(f"[{index}/{len(SCENARIOS)}] {out_path.name}: "
                  f"{len(tool_call_log)} tool calls, tools={sample['tools_used']}")

    print(f"\nArchived {len(collected)} samples to {EVIDENCE_DIR}")
    fallback_runs = [
        path.name for path, _, tools in collected if "react_fallback" in tools
    ]
    if fallback_runs:
        print(f"WARNING: fallback fired in {fallback_runs}; consider re-running those samples.")


if __name__ == "__main__":
    os.chdir(BACKEND_DIR)
    main()
