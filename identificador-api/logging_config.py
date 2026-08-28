import json
import logging
import sys
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any

from env_util import env_str

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
search_id_var: ContextVar[str | None] = ContextVar("search_id", default=None)

_LOG_RECORD_RESERVED = frozenset(
    logging.makeLogRecord({}).__dict__.keys()
) | {"message", "asctime"}


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()  # type: ignore[attr-defined]
        record.search_id = search_id_var.get()  # type: ignore[attr-defined]
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id
        search_id = getattr(record, "search_id", None)
        if search_id:
            payload["search_id"] = search_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _LOG_RECORD_RESERVED and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


class StructuredTextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        context: list[str] = []
        request_id = getattr(record, "request_id", None)
        if request_id:
            context.append(f"request_id={request_id}")
        search_id = getattr(record, "search_id", None)
        if search_id:
            context.append(f"search_id={search_id}")
        for key in ("event", "code", "engine", "phase", "status", "path", "method"):
            value = getattr(record, key, None)
            if value is not None:
                context.append(f"{key}={value}")
        if context:
            return f"{base} [{', '.join(context)}]"
        return base


def configure_logging() -> None:
    level_name = env_str("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    log_format = env_str(
        "LOG_FORMAT",
        "json" if env_str("ENVIRONMENT") == "production" else "text",
    )
    use_json = log_format.lower() == "json"

    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextFilter())
    if use_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            StructuredTextFormatter(
                fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
    root.setLevel(level)
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


@contextmanager
def search_id_context(search_id: str):
    token: Token = search_id_var.set(search_id)
    try:
        yield
    finally:
        search_id_var.reset(token)


@contextmanager
def request_id_context(request_id: str):
    token: Token = request_id_var.set(request_id)
    try:
        yield
    finally:
        request_id_var.reset(token)
