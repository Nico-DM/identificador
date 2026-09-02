from datetime import UTC, datetime


def utc_dt(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
) -> datetime:
    """Return a naive UTC datetime (matches identificador conventions)."""
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC).replace(
        tzinfo=None
    )
