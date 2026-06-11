"""
Phase 2 Agent Tools — MCP Server (Step E, USE_MCP_TOOLS)

Exposes the SAME tools as the direct ToolRegistry over the Model Context
Protocol, so external MCP clients (Claude Desktop, Cursor) can drive the
interview toolkit. Parity with direct tools is verified by
tests/test_mcp_parity.py.

Run standalone (stdio transport):
    python -m app.agent.mcp_server

Claude Desktop config example:
    {
      "mcpServers": {
        "smartsuccess-interview": {
          "command": "python",
          "args": ["-m", "app.agent.mcp_server"],
          "cwd": "/path/to/smartsuccess-interview-backend"
        }
      }
    }
"""

import logging
from typing import Dict, List, Optional

from app.agent.tools import AgentToolkit

logger = logging.getLogger(__name__)

try:
    from mcp.server.fastmcp import FastMCP
    MCP_AVAILABLE = True
except ImportError:  # mcp is an optional dependency
    FastMCP = None
    MCP_AVAILABLE = False


# Stateless toolkit shared by MCP tool handlers. score_answer runs in
# heuristic mode here (no LLM injected) so results are deterministic and
# directly comparable with the direct toolkit in parity tests.
_toolkit = AgentToolkit()

if MCP_AVAILABLE:
    mcp = FastMCP("smartsuccess-interview-tools")
else:
    mcp = None


def mcp_search_question_bank(
    interview_type: str,
    category: Optional[str] = None,
    exclude_ids: Optional[List[str]] = None,
    limit: int = 3,
) -> Dict:
    """Search the interview question bank (same as direct tool)."""
    return _toolkit.search_question_bank(
        interview_type=interview_type,
        category=category,
        exclude_ids=exclude_ids,
        limit=limit,
    )


async def mcp_score_answer(
    question: str, answer: str, interview_type: str = "screening"
) -> Dict:
    """Score a candidate answer on the rubric (same as direct tool)."""
    return await _toolkit.score_answer(
        question=question, answer=answer, interview_type=interview_type
    )


def mcp_save_interview_note(note: str, category: str = "general") -> Dict:
    """Save an interviewer observation (same as direct tool)."""
    return _toolkit.save_interview_note(note=note, category=category)


if MCP_AVAILABLE:
    # Register the plain functions as MCP tools under the SAME names as
    # the direct ToolRegistry, preserving tool-name parity.
    mcp.tool(name="search_question_bank")(mcp_search_question_bank)
    mcp.tool(name="score_answer")(mcp_score_answer)
    mcp.tool(name="save_interview_note")(mcp_save_interview_note)


if __name__ == "__main__":
    if not MCP_AVAILABLE:
        raise SystemExit(
            "The 'mcp' package is not installed. Run: pip install mcp"
        )
    mcp.run()  # stdio transport by default
