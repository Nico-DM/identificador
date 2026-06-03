import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass
from threading import Lock

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def _parse_positive_int(value: str | None, fallback: int) -> int:
    if not value or not value.strip():
        return fallback
    try:
        parsed = int(value.strip(), 10)
    except ValueError:
        return fallback
    if parsed <= 0:
        return fallback
    return parsed


def _parse_bool(value: str | None, fallback: bool) -> bool:
    if not value or not value.strip():
        return fallback
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return fallback


RATE_LIMIT_ENABLED = _parse_bool(
    os.getenv("RATE_LIMIT_ENABLED"),
    os.getenv("ENVIRONMENT", "development") != "development",
)
RATE_LIMIT_SEARCH_PER_HOUR = _parse_positive_int(
    os.getenv("RATE_LIMIT_SEARCH_PER_HOUR"),
    10,
)
RATE_LIMIT_DEEP_PER_HOUR = _parse_positive_int(
    os.getenv("RATE_LIMIT_DEEP_PER_HOUR"),
    5,
)
RATE_LIMIT_RESULTS_PER_MINUTE = _parse_positive_int(
    os.getenv("RATE_LIMIT_RESULTS_PER_MINUTE"),
    300,
)


@dataclass
class _Bucket:
    count: int = 0
    window_start: float = 0.0


class FixedWindowLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = defaultdict(_Bucket)
        self._lock = Lock()
        self._last_cleanup = time.monotonic()

    def check(self, key: str, limit: int, window_seconds: int) -> int:
        """Returns seconds until retry if exceeded, 0 if allowed."""
        now = time.monotonic()
        with self._lock:
            self._maybe_cleanup(now)
            bucket = self._buckets[key]
            if now - bucket.window_start >= window_seconds:
                bucket.window_start = now
                bucket.count = 0
            if bucket.count >= limit:
                retry_after = int(window_seconds - (now - bucket.window_start)) + 1
                return max(1, retry_after)
            bucket.count += 1
            return 0

    def _maybe_cleanup(self, now: float) -> None:
        if now - self._last_cleanup < 600:
            return
        self._last_cleanup = now
        stale = [k for k, b in self._buckets.items() if now - b.window_start > 7200]
        for key in stale:
            del self._buckets[key]


_limiter = FixedWindowLimiter()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return "unknown"


def enforce_rate_limit(
    request: Request,
    *,
    namespace: str,
    limit: int,
    window_seconds: int,
) -> None:
    if not RATE_LIMIT_ENABLED or limit <= 0:
        return
    ip = client_ip(request)
    key = f"{namespace}:{ip}"
    retry_after = _limiter.check(key, limit, window_seconds)
    if retry_after > 0:
        logger.warning("Rate limit exceeded for %s (namespace=%s)", ip, namespace)
        raise HTTPException(
            status_code=429,
            detail=f"Demasiadas solicitudes. Intenta de nuevo en {retry_after} s.",
            headers={"Retry-After": str(retry_after)},
        )


def rate_limit_search(request: Request) -> None:
    enforce_rate_limit(
        request,
        namespace="search",
        limit=RATE_LIMIT_SEARCH_PER_HOUR,
        window_seconds=3600,
    )


def rate_limit_deep(request: Request) -> None:
    enforce_rate_limit(
        request,
        namespace="deep",
        limit=RATE_LIMIT_DEEP_PER_HOUR,
        window_seconds=3600,
    )


def rate_limit_results(request: Request) -> None:
    enforce_rate_limit(
        request,
        namespace="results",
        limit=RATE_LIMIT_RESULTS_PER_MINUTE,
        window_seconds=60,
    )
