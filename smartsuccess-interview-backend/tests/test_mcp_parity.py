"""
Phase 2 MCP parity tests (PRD 02 §9: "compare schemas with direct tools").

Direct-binding (USE_AGENT_TOOLS) and MCP (USE_MCP_TOOLS) paths must share one
implementation, so the exposed tool surfaces have to stay in lockstep.
"""

import inspect

import pytest

from app.agents.tools import fetch_resume_context, search_question_bank
from app.mcp_server import server as mcp_server_module
from app.mcp_server.server import MCP_SERVER_AVAILABLE, get_mcp_smoke_registry

DIRECT_TOOLS = {
    "search_question_bank": search_question_bank,
    "fetch_resume_context": fetch_resume_context,
}


def test_mcp_registry_signatures_match_direct_tool_schemas():
    """Registry handlers must accept exactly the parameters the direct tools declare."""
    registry = get_mcp_smoke_registry()
    assert set(registry) == set(DIRECT_TOOLS)

    for name, direct_tool in DIRECT_TOOLS.items():
        direct_params = set(direct_tool.args.keys())
        handler_params = set(inspect.signature(registry[name]).parameters.keys())
        assert handler_params == direct_params, (
            f"{name}: MCP handler params {handler_params} "
            f"!= direct tool params {direct_params}"
        )


def test_mcp_registry_defaults_match_direct_tools():
    """Optional-parameter defaults must be identical across both transports."""
    registry = get_mcp_smoke_registry()
    for name, direct_tool in DIRECT_TOOLS.items():
        handler_sig = inspect.signature(registry[name])
        for param_name, schema in direct_tool.args.items():
            if "default" not in schema:
                continue
            handler_default = handler_sig.parameters[param_name].default
            assert handler_default == schema["default"], (
                f"{name}.{param_name}: MCP default {handler_default!r} "
                f"!= direct default {schema['default']!r}"
            )


@pytest.mark.asyncio
@pytest.mark.skipif(not MCP_SERVER_AVAILABLE, reason="`mcp` package not installed")
async def test_fastmcp_server_exposes_parity_tools():
    """FastMCP runtime tool list must cover both shared tools with matching params."""
    server = mcp_server_module.create_mcp_server()
    mcp_tools = await server.list_tools()
    tools_by_name = {tool.name: tool for tool in mcp_tools}

    expected = {
        "search_question_bank_tool": "search_question_bank",
        "fetch_resume_context_tool": "fetch_resume_context",
    }
    assert set(expected).issubset(tools_by_name), sorted(tools_by_name)

    for mcp_name, direct_name in expected.items():
        mcp_props = set(tools_by_name[mcp_name].inputSchema.get("properties", {}).keys())
        direct_params = set(DIRECT_TOOLS[direct_name].args.keys())
        assert mcp_props == direct_params, (
            f"{mcp_name}: MCP schema {mcp_props} != direct schema {direct_params}"
        )
