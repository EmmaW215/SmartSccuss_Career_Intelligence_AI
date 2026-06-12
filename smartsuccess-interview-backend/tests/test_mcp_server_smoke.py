"""
MCP minimal baseline smoke tests:
- tools/list
- tools/call
"""

import pytest

from app.mcp_server.server import get_mcp_smoke_registry


@pytest.mark.asyncio
async def test_mcp_smoke_tools_list_and_call():
    registry = get_mcp_smoke_registry()
    assert "search_question_bank" in registry
    assert "fetch_resume_context" in registry

    search_result = await registry["search_question_bank"](
        query="system design",
        category="technical",
        k=2,
    )
    assert isinstance(search_result, list)
    assert len(search_result) <= 2

    resume_result = await registry["fetch_resume_context"](
        user_id="smoke_user_001",
        query="langgraph",
        k=2,
    )
    assert isinstance(resume_result, list)
