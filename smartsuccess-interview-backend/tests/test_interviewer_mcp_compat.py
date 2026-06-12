"""
Interviewer MCP compatibility tests.
"""

import asyncio

import pytest

from app.agents import interviewer_agent as interviewer_module
from app.config import settings


@pytest.fixture(autouse=True)
def _reset_interviewer_agent_cache():
    interviewer_module.reset_interviewer_agent_runtime_cache()
    yield
    interviewer_module.reset_interviewer_agent_runtime_cache()


@pytest.mark.asyncio
async def test_load_interviewer_tools_prefers_mcp_when_available(monkeypatch):
    monkeypatch.setattr(settings, "use_mcp_tools", True)
    dummy_tools = [object()]

    async def _fake_load_mcp_tools():
        return dummy_tools

    monkeypatch.setattr(interviewer_module, "_load_mcp_tools", _fake_load_mcp_tools)
    monkeypatch.setattr(interviewer_module, "get_agent_tools", lambda: [object(), object()])

    tools = await interviewer_module._load_interviewer_tools()
    assert tools is dummy_tools


@pytest.mark.asyncio
async def test_load_interviewer_tools_falls_back_to_direct(monkeypatch):
    monkeypatch.setattr(settings, "use_mcp_tools", True)

    async def _fake_load_mcp_tools():
        return []

    direct_tools = [object()]
    monkeypatch.setattr(interviewer_module, "_load_mcp_tools", _fake_load_mcp_tools)
    monkeypatch.setattr(interviewer_module, "get_agent_tools", lambda: direct_tools)

    tools = await interviewer_module._load_interviewer_tools()
    assert tools is direct_tools


@pytest.mark.asyncio
async def test_load_mcp_tools_recovers_after_transient_error(monkeypatch):
    monkeypatch.setattr(settings, "mcp_server_url", "http://localhost:8000/mcp")
    build_calls = {"count": 0}

    class _FailClient:
        async def get_tools(self):
            raise RuntimeError("temporary outage")

    class _SuccessClient:
        async def get_tools(self):
            return [object()]

    def _fake_build_client():
        build_calls["count"] += 1
        if build_calls["count"] == 1:
            return _FailClient()
        return _SuccessClient()

    monkeypatch.setattr(interviewer_module, "_build_mcp_client", _fake_build_client)

    first = await interviewer_module._load_mcp_tools()
    second = await interviewer_module._load_mcp_tools()

    assert first == []
    assert len(second) == 1
    # Verify failure path did not poison cache.
    assert build_calls["count"] == 2


@pytest.mark.asyncio
async def test_load_mcp_tools_uses_lock_for_concurrent_initialization(monkeypatch):
    monkeypatch.setattr(settings, "mcp_server_url", "http://localhost:8000/mcp")
    build_calls = {"count": 0}

    class _SlowClient:
        async def get_tools(self):
            await asyncio.sleep(0.05)
            return [object()]

    def _fake_build_client():
        build_calls["count"] += 1
        return _SlowClient()

    monkeypatch.setattr(interviewer_module, "_build_mcp_client", _fake_build_client)

    result_a, result_b = await asyncio.gather(
        interviewer_module._load_mcp_tools(),
        interviewer_module._load_mcp_tools(),
    )

    assert len(result_a) == 1
    assert len(result_b) == 1
    # Concurrency-safe: only one client initialization should happen.
    assert build_calls["count"] == 1
