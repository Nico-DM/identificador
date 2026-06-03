from datetime import datetime
from typing import Any


def _encode_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _encode_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_encode_value(item) for item in value]
    return value


def to_jsonable(data: Any) -> Any:
    if data is None:
        return None
    return _encode_value(data)


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        return parsed.astimezone().replace(tzinfo=None)
    return parsed


def _decode_value(value: Any) -> Any:
    if isinstance(value, str):
        if len(value) >= 10 and value[4] == "-" and value[10] in "T ":
            try:
                return _parse_datetime(value)
            except ValueError:
                return value
        return value
    if isinstance(value, dict):
        return {k: _decode_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode_value(item) for item in value]
    return value


def from_jsonable(data: Any) -> Any:
    if data is None:
        return None
    return _decode_value(data)
