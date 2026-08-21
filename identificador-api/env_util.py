import os


def env_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def parse_positive_int(value: str | None, fallback: int) -> int:
    if not value or not value.strip():
        return fallback
    try:
        parsed = int(value.strip(), 10)
    except ValueError:
        return fallback
    if parsed <= 0:
        return fallback
    return parsed


def parse_bool(value: str | None, fallback: bool) -> bool:
    if not value or not value.strip():
        return fallback
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return fallback


def parse_float(
    value: str | None,
    fallback: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if not value or not value.strip():
        return fallback
    try:
        parsed = float(value.strip())
    except ValueError:
        return fallback
    if minimum is not None and parsed < minimum:
        return fallback
    if maximum is not None and parsed > maximum:
        return fallback
    return parsed


def parse_safe_search(value) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    return normalized not in {"0", "false", "no", "off"}
