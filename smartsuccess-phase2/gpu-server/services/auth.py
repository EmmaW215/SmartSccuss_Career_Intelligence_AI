"""
Phase 4 PR 4-2 — internal service authentication for the GPU server.

The GPU host is reachable over a public tunnel (Cloudflare/Tailscale), so the
inference endpoints are gated by a shared secret (`X-Internal-Token`). Pure,
dependency-free logic so it is unit-testable without torch/FastAPI.

Backward compatible: when INTERNAL_API_TOKEN is unset the gate is disabled and
the server behaves exactly as before — so an existing deploy that hasn't set
the token keeps working.
"""

from __future__ import annotations

import secrets

INTERNAL_TOKEN_HEADER = "X-Internal-Token"

# Always reachable without a token: liveness/monitoring/docs. Inference and
# ops-data endpoints (/api/*, /metrics) require the token when one is set.
PUBLIC_PATHS = frozenset(
    {"/health", "/health/detail", "/", "/docs", "/redoc", "/openapi.json"}
)


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS


def is_authorized(path: str, provided_token: str, configured_token: str) -> bool:
    """
    Decide whether a request may proceed.

    - No configured token  -> auth disabled, everything allowed (legacy behavior)
    - Public path          -> always allowed
    - Otherwise            -> constant-time match of the provided token
    """
    if not configured_token:
        return True
    if is_public_path(path):
        return True
    if not provided_token:
        return False
    return secrets.compare_digest(provided_token, configured_token)
