"""
Phase 4 PR 4-2 — internal-token auth gate (torch-free unit tests).

Loaded by file path to avoid executing services/__init__.py (which imports
torch via tts_service).
"""

import importlib.util
from pathlib import Path

_AUTH_PATH = Path(__file__).resolve().parents[1] / "services" / "auth.py"
_spec = importlib.util.spec_from_file_location("gpu_auth_under_test", _AUTH_PATH)
_auth = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_auth)

is_authorized = _auth.is_authorized
is_public_path = _auth.is_public_path
PUBLIC_PATHS = _auth.PUBLIC_PATHS

TOKEN = "s3cret-token"


class TestAuthDisabledWhenNoTokenConfigured:
    def test_everything_allowed_when_token_unset(self):
        # Legacy behavior: no configured token -> auth off, all paths allowed.
        assert is_authorized("/api/stt/transcribe", "", "") is True
        assert is_authorized("/metrics", "", "") is True
        assert is_authorized("/api/rag/build", "anything", "") is True


class TestPublicPaths:
    def test_health_and_docs_always_public(self):
        for path in ("/health", "/health/detail", "/", "/docs", "/openapi.json", "/redoc"):
            assert is_public_path(path) is True
            # Public even with a configured token and no header provided.
            assert is_authorized(path, "", TOKEN) is True

    def test_api_paths_are_not_public(self):
        assert is_public_path("/api/stt/transcribe") is False
        assert is_public_path("/metrics") is False


class TestProtectedPathsWhenTokenConfigured:
    def test_correct_token_allowed(self):
        assert is_authorized("/api/stt/transcribe", TOKEN, TOKEN) is True
        assert is_authorized("/metrics", TOKEN, TOKEN) is True

    def test_missing_token_rejected(self):
        assert is_authorized("/api/stt/transcribe", "", TOKEN) is False

    def test_wrong_token_rejected(self):
        assert is_authorized("/api/stt/transcribe", "wrong", TOKEN) is False
        assert is_authorized("/api/rag/build", "s3cret-toke", TOKEN) is False  # near-miss
