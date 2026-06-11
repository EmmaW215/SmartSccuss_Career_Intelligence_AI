"""
Phase 2 Agent Tools — MCP parity tests (Step E, USE_MCP_TOOLS)

Verifies the MCP server exposes the SAME tools with the SAME behavior as
the direct ToolRegistry used by the in-process agent.
"""

import pytest

mcp_module = pytest.importorskip(
    "mcp", reason="mcp package not installed (pip install mcp)"
)

from app.agent import mcp_server
from app.agent.registry import ToolRegistry
from app.agent.tools import AgentToolkit

ANSWER = (
    "I led the FastAPI migration at TechCorp, cutting p95 latency 40% and "
    "saving $2000 a month across our GCP deployment."
)


class TestMCPParity:

    def test_mcp_server_available(self):
        assert mcp_server.MCP_AVAILABLE
        assert mcp_server.mcp is not None

    async def test_mcp_exposes_direct_tool_names(self):
        """Every MCP tool name must exist in the direct registry."""
        mcp_tools = {t.name for t in await mcp_server.mcp.list_tools()}
        direct_tools = set(ToolRegistry().tool_names)
        assert mcp_tools <= direct_tools
        assert {"search_question_bank", "score_answer"} <= mcp_tools

    def test_search_question_bank_parity(self):
        direct = AgentToolkit().search_question_bank(
            "screening", category="motivation", limit=5
        )
        via_mcp = mcp_server.mcp_search_question_bank(
            "screening", category="motivation", limit=5
        )
        assert via_mcp == direct

    def test_search_error_payload_parity(self):
        direct = AgentToolkit().search_question_bank("astrology")
        via_mcp = mcp_server.mcp_search_question_bank("astrology")
        assert via_mcp == direct
        assert via_mcp["ok"] is False

    async def test_score_answer_parity(self):
        """Heuristic scoring is deterministic, so direct and MCP results
        must be identical for identical input."""
        direct = await AgentToolkit().score_answer(
            question="Tell me about a project.",
            answer=ANSWER,
            interview_type="technical",
        )
        via_mcp = await mcp_server.mcp_score_answer(
            question="Tell me about a project.",
            answer=ANSWER,
            interview_type="technical",
        )
        assert via_mcp == direct
        assert via_mcp["method"] == "heuristic"

    async def test_mcp_call_tool_roundtrip(self):
        """Full MCP call_tool path returns the same payload as direct."""
        result = await mcp_server.mcp.call_tool(
            "search_question_bank", {"interview_type": "behavioral", "limit": 2}
        )
        direct = AgentToolkit().search_question_bank("behavioral", limit=2)
        # FastMCP returns (content, structured_result) or content list
        # depending on version — normalize to the structured dict.
        structured = None
        if isinstance(result, tuple) and len(result) == 2:
            structured = result[1]
            if isinstance(structured, dict) and "result" in structured:
                structured = structured["result"]
        if structured is None:
            import json
            structured = json.loads(result[0].text)
        assert structured == direct
