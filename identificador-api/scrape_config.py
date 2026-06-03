import os

DEFAULT_STATIC_MAX_WORKERS = 8
DEFAULT_DYNAMIC_MAX_WORKERS = 2
DEFAULT_STATIC_CONFIDENCE_THRESHOLD = 0.55


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


def _parse_float(value: str | None, fallback: float) -> float:
    if not value or not value.strip():
        return fallback
    try:
        parsed = float(value.strip())
    except ValueError:
        return fallback
    if parsed < 0 or parsed > 1:
        return fallback
    return parsed


SCRAPE_STATIC_MAX_WORKERS = _parse_positive_int(
    os.getenv("SCRAPE_STATIC_MAX_WORKERS"),
    DEFAULT_STATIC_MAX_WORKERS,
)
SCRAPE_DYNAMIC_MAX_WORKERS = _parse_positive_int(
    os.getenv("SCRAPE_DYNAMIC_MAX_WORKERS"),
    DEFAULT_DYNAMIC_MAX_WORKERS,
)
SCRAPE_STATIC_CONFIDENCE_THRESHOLD = _parse_float(
    os.getenv("SCRAPE_STATIC_CONFIDENCE_THRESHOLD"),
    DEFAULT_STATIC_CONFIDENCE_THRESHOLD,
)
SCRAPE_DYNAMIC_ENABLED = _parse_bool(os.getenv("SCRAPE_DYNAMIC_ENABLED"), True)
