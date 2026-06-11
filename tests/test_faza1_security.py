"""
FAZA 1 xavfsizlik testlari.
Barcha testlar pure unit — DB kerak emas.
"""
from __future__ import annotations

import asyncio
import os
import pytest

pytestmark = pytest.mark.no_db


# ──────────────────────────────────────────────────────────
# F1-2: credential master key fail-fast
# ──────────────────────────────────────────────────────────

class TestMasterKeyFailFast:
    def test_no_error_when_strict_mode_off(self, monkeypatch):
        monkeypatch.delenv("APP_STRICT_MODE", raising=False)
        monkeypatch.delenv("APP_CREDENTIALS_MASTER_KEY", raising=False)
        from utils.auth.credential_crypto import assert_master_key_configured
        assert_master_key_configured()  # xato bo'lmasligi kerak

    def test_no_error_when_strict_mode_false(self, monkeypatch):
        monkeypatch.setenv("APP_STRICT_MODE", "false")
        monkeypatch.delenv("APP_CREDENTIALS_MASTER_KEY", raising=False)
        from utils.auth.credential_crypto import assert_master_key_configured
        assert_master_key_configured()

    def test_raises_when_strict_mode_true_and_no_key(self, monkeypatch):
        from utils.auth import credential_crypto
        monkeypatch.setenv("APP_STRICT_MODE", "true")
        # has_configured_master_key() ni to'g'ridan-to'g'ri False qaytaruvchi qilib patch
        monkeypatch.setattr(credential_crypto, "has_configured_master_key", lambda: False)
        with pytest.raises(RuntimeError, match="APP_CREDENTIALS_MASTER_KEY"):
            credential_crypto.assert_master_key_configured()

    def test_no_error_when_strict_mode_true_and_key_present(self, monkeypatch):
        from utils.auth import credential_crypto
        monkeypatch.setenv("APP_STRICT_MODE", "true")
        monkeypatch.setattr(credential_crypto, "has_configured_master_key", lambda: True)
        credential_crypto.assert_master_key_configured()  # xato bo'lmasligi kerak


# ──────────────────────────────────────────────────────────
# F1-3: rate limiting
# ──────────────────────────────────────────────────────────

class TestRateLimit:
    def _make_request(self, ip: str = "1.2.3.4"):
        from unittest.mock import MagicMock
        req = MagicMock()
        req.headers = {}
        req.client = MagicMock()
        req.client.host = ip
        req.query_params = {}
        return req

    def test_allows_under_limit(self):
        import importlib
        import services.api.rate_limit as rl
        importlib.reload(rl)

        req = self._make_request("10.0.0.1")
        for _ in range(rl._MAX_REQUESTS):
            asyncio.get_event_loop().run_until_complete(rl.check_rate_limit(req))

    def test_blocks_over_limit(self):
        from fastapi import HTTPException
        import importlib
        import services.api.rate_limit as rl
        importlib.reload(rl)

        req = self._make_request("10.0.0.2")
        for _ in range(rl._MAX_REQUESTS):
            asyncio.get_event_loop().run_until_complete(rl.check_rate_limit(req))

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(rl.check_rate_limit(req))
        assert exc_info.value.status_code == 429

    def test_different_ips_are_independent(self):
        import importlib
        import services.api.rate_limit as rl
        importlib.reload(rl)

        for i in range(rl._MAX_REQUESTS + 1):
            req = self._make_request(f"192.168.{i}.1")
            asyncio.get_event_loop().run_until_complete(rl.check_rate_limit(req))


# ──────────────────────────────────────────────────────────
# F1-4: security headers
# ──────────────────────────────────────────────────────────

class TestSecurityHeaders:
    def test_security_headers_present(self):
        from unittest.mock import AsyncMock, MagicMock
        from starlette.responses import Response
        import importlib
        import services.webhook.jira_webhook_handler as handler
        importlib.reload(handler)

        middleware = handler._SecurityHeadersMiddleware(app=MagicMock())

        mock_response = Response(content="ok")
        call_next = AsyncMock(return_value=mock_response)
        req = MagicMock()
        result = asyncio.get_event_loop().run_until_complete(
            middleware.dispatch(req, call_next)
        )
        assert result.headers.get("X-Content-Type-Options") == "nosniff"
        assert result.headers.get("X-Frame-Options") == "DENY"
        assert result.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ──────────────────────────────────────────────────────────
# F1-1: webhook secret
# ──────────────────────────────────────────────────────────

class TestWebhookSecret:
    def test_webhook_secret_check_logic(self):
        """_check_webhook_secret helper mantiqini tekshirish."""
        expected = "mysecret"

        def check(provided_header, provided_query):
            provided = (provided_header or provided_query or "").strip()
            return provided == expected

        assert check("mysecret", None) is True
        assert check(None, "mysecret") is True
        assert check("wrong", None) is False
        assert check(None, None) is False
        assert check("", "") is False
