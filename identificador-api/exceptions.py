from __future__ import annotations

import requests


class IdentificadorError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "INTERNAL_ERROR",
        http_status: int = 500,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


class ValidationError(IdentificadorError):
    def __init__(self, message: str, *, code: str = "VALIDATION_ERROR") -> None:
        super().__init__(message, code=code, http_status=400)


class NotFoundError(IdentificadorError):
    def __init__(self, message: str, *, code: str = "NOT_FOUND") -> None:
        super().__init__(message, code=code, http_status=404)


class ConflictError(IdentificadorError):
    def __init__(self, message: str, *, code: str = "CONFLICT") -> None:
        super().__init__(message, code=code, http_status=409)


class RateLimitError(IdentificadorError):
    def __init__(
        self,
        message: str,
        *,
        retry_after: int,
        code: str = "RATE_LIMIT_EXCEEDED",
    ) -> None:
        super().__init__(message, code=code, http_status=429)
        self.retry_after = retry_after


class ServiceUnavailableError(IdentificadorError):
    def __init__(
        self, message: str, *, code: str = "SERVICE_UNAVAILABLE"
    ) -> None:
        super().__init__(message, code=code, http_status=503)


class ConfigurationError(IdentificadorError):
    def __init__(self, message: str, *, code: str = "CONFIGURATION_ERROR") -> None:
        super().__init__(message, code=code, http_status=503)


class ExternalServiceError(IdentificadorError):
    def __init__(
        self, message: str, *, code: str = "EXTERNAL_SERVICE_ERROR"
    ) -> None:
        super().__init__(message, code=code, http_status=502)


def classify_background_error(exc: BaseException) -> tuple[str, str]:
    if isinstance(exc, IdentificadorError):
        return exc.code, exc.message
    if isinstance(exc, requests.RequestException):
        return "NETWORK_ERROR", "Error de conexion con un servicio externo"
    return "INTERNAL_ERROR", "Error interno del procesamiento"
