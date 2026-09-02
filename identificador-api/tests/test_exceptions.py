import requests
from exceptions import (
    ConfigurationError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
    classify_background_error,
)


class TestExceptionClasses:
    def test_validation_error(self):
        exc = ValidationError("bad input")
        assert exc.http_status == 400
        assert exc.code == "VALIDATION_ERROR"
        assert exc.message == "bad input"

    def test_not_found_error(self):
        exc = NotFoundError("missing")
        assert exc.http_status == 404

    def test_conflict_error(self):
        exc = ConflictError("busy")
        assert exc.http_status == 409

    def test_rate_limit_error(self):
        exc = RateLimitError("slow down", retry_after=30)
        assert exc.http_status == 429
        assert exc.retry_after == 30

    def test_service_unavailable(self):
        exc = ServiceUnavailableError("down")
        assert exc.http_status == 503

    def test_configuration_error(self):
        exc = ConfigurationError("misconfigured")
        assert exc.http_status == 503

    def test_external_service_error(self):
        exc = ExternalServiceError("upstream")
        assert exc.http_status == 502


class TestClassifyBackgroundError:
    def test_identificador_error(self):
        exc = ValidationError("invalid")
        code, message = classify_background_error(exc)
        assert code == "VALIDATION_ERROR"
        assert message == "invalid"

    def test_request_exception(self):
        exc = requests.ConnectionError("timeout")
        code, message = classify_background_error(exc)
        assert code == "NETWORK_ERROR"
        assert "conexion" in message.lower()

    def test_generic_exception(self):
        code, message = classify_background_error(RuntimeError("boom"))
        assert code == "INTERNAL_ERROR"
        assert "interno" in message.lower()
