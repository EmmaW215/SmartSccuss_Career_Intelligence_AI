"""
Phase 4 PR 4-2 — Render-side gpu_client must send X-Internal-Token when set,
and send nothing when unset (legacy behavior preserved).
"""

import pytest

from app.config import settings
from app.services.gpu_client import GPUClient


@pytest.mark.asyncio
async def test_token_header_attached_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "internal_api_token", "abc123token")
    client = GPUClient()
    http = await client._get_client()
    try:
        assert http.headers.get("X-Internal-Token") == "abc123token"
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_no_token_header_when_unset(monkeypatch):
    monkeypatch.setattr(settings, "internal_api_token", "")
    client = GPUClient()
    http = await client._get_client()
    try:
        assert "X-Internal-Token" not in http.headers
    finally:
        await http.aclose()
