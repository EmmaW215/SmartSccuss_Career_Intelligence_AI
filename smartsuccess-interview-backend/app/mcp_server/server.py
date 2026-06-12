"""
Minimal MCP baseline server for Phase 2.

Provides shared implementations for:
- tools/list smoke checks
- tools/call smoke checks
- optional FastMCP runtime registration
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, List

from app.agents.tools import fetch_resume_context, search_question_bank

logger = logging.getLogger(__name__)

try:
    from mcp.server.fastmcp import FastMCP

    MCP_SERVER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):  # pragma: no cover - optional dependency
    FastMCP = None  # type: ignore[assignment]
    MCP_SERVER_AVAILABLE = False


ToolHandler = Callable[..., Awaitable[Any]]


class MCPToolAdapter:
    """
    Shared tool registry used by FastMCP runtime and smoke tests.
    """

    @staticmethod
    async def search_question_bank(query: str, category: str = "general", k: int = 3) -> List[Dict[str, Any]]:
        result = await search_question_bank.ainvoke(
            {"query": query, "category": category, "k": k}
        )
        return result if isinstance(result, list) else []

    @staticmethod
    async def fetch_resume_context(user_id: str, query: str, k: int = 3) -> List[str]:
        result = await fetch_resume_context.ainvoke(
            {"user_id": user_id, "query": query, "k": k}
        )
        return result if isinstance(result, list) else []


_TOOL_REGISTRY: Dict[str, ToolHandler] = {
    "search_question_bank": MCPToolAdapter.search_question_bank,
    "fetch_resume_context": MCPToolAdapter.fetch_resume_context,
}


def get_mcp_smoke_registry() -> Dict[str, ToolHandler]:
    return dict(_TOOL_REGISTRY)


def create_mcp_server() -> Any:
    """
    Create FastMCP server instance if dependency is available.
    """
    if not MCP_SERVER_AVAILABLE or FastMCP is None:
        raise RuntimeError(
            "MCP server dependency is not installed. "
            "Install `mcp` to enable streamable-http MCP runtime."
        )

    mcp = FastMCP("smartsuccess-interview-knowledge")

    @mcp.tool()
    async def search_question_bank_tool(
        query: str, category: str = "general", k: int = 3
    ) -> List[Dict[str, Any]]:
        return await MCPToolAdapter.search_question_bank(
            query=query, category=category, k=k
        )

    @mcp.tool()
    async def fetch_resume_context_tool(
        user_id: str, query: str, k: int = 3
    ) -> List[str]:
        return await MCPToolAdapter.fetch_resume_context(
            user_id=user_id, query=query, k=k
        )

    @mcp.resource("questionbank://categories")
    async def list_question_categories() -> str:
        return "screening,behavioral,technical,general"

    return mcp


if __name__ == "__main__":
    # Standalone stdio mode for Claude Desktop / Cursor demos:
    #   python -m app.mcp_server.server
    create_mcp_server().run()
