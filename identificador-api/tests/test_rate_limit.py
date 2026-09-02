import time

import pytest
from exceptions import RateLimitError
from fastapi import Request
from rate_limit import FixedWindowLimiter, client_ip, enforce_rate_limit


class TestFixedWindowLimiter:
    def test_allows_within_limit(self):
        limiter = FixedWindowLimiter()
        assert limiter.check("key1", limit=3, window_seconds=60) == 0
        assert limiter.check("key1", limit=3, window_seconds=60) == 0
        assert limiter.check("key1", limit=3, window_seconds=60) == 0

    def test_blocks_when_exceeded(self):
        limiter = FixedWindowLimiter()
        for _ in range(2):
            assert limiter.check("key2", limit=2, window_seconds=60) == 0
        retry_after = limiter.check("key2", limit=2, window_seconds=60)
        assert retry_after >= 1

    def test_window_resets(self):
        limiter = FixedWindowLimiter()
        limiter.check("key3", limit=1, window_seconds=1)
        assert limiter.check("key3", limit=1, window_seconds=1) > 0
        time.sleep(1.1)
        assert limiter.check("key3", limit=1, window_seconds=1) == 0

    def test_separate_keys_independent(self):
        limiter = FixedWindowLimiter()
        assert limiter.check("a", limit=1, window_seconds=60) == 0
        assert limiter.check("b", limit=1, window_seconds=60) == 0


class TestClientIp:
    def _make_request(self, headers: dict, client_host: str | None = "127.0.0.1"):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
            "client": (client_host, 12345) if client_host else None,
        }
        return Request(scope)

    def test_x_forwarded_for(self):
        req = self._make_request({"X-Forwarded-For": "1.2.3.4, 5.6.7.8"})
        assert client_ip(req) == "1.2.3.4"

    def test_x_real_ip(self):
        req = self._make_request({"X-Real-IP": "10.0.0.1"})
        assert client_ip(req) == "10.0.0.1"

    def test_client_host_fallback(self):
        req = self._make_request({})
        assert client_ip(req) == "127.0.0.1"

    def test_unknown_when_no_client(self):
        req = self._make_request({}, client_host=None)
        assert client_ip(req) == "unknown"


class TestEnforceRateLimit:
    def test_disabled_does_not_raise(self, monkeypatch):
        monkeypatch.setattr("rate_limit.RATE_LIMIT_ENABLED", False)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }
        enforce_rate_limit(
            Request(scope),
            namespace="test",
            limit=1,
            window_seconds=60,
        )

    def test_raises_when_exceeded(self, monkeypatch):
        monkeypatch.setattr("rate_limit.RATE_LIMIT_ENABLED", True)
        limiter = FixedWindowLimiter()
        monkeypatch.setattr("rate_limit._limiter", limiter)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": ("9.9.9.9", 12345),
        }
        req = Request(scope)

        enforce_rate_limit(req, namespace="exceeded", limit=1, window_seconds=3600)
        with pytest.raises(RateLimitError):
            enforce_rate_limit(req, namespace="exceeded", limit=1, window_seconds=3600)
