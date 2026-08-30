"""Tests for the structured exception logging helper ``log_exception``.

These tests verify that the helper produces correctly structured log entries
with all required context fields, without modifying the application's logging
configuration.
"""

from datetime import datetime
from unittest.mock import MagicMock
import structlog

from app.core.logging import log_exception


class FakeRequest:
    """Minimal FastAPI Request mock for test purposes."""

    def __init__(self, method: str = "GET", path: str = "/test", host: str = "127.0.0.1"):
        self.method = method
        self.url = MagicMock()
        self.url.path = path
        self.client = MagicMock()
        self.client.host = host
        self.state = MagicMock()
        self.state.request_id = "test-request-id"


def test_log_exception_minimal_fields() -> None:
    """The helper must include exception_type, exception_message, traceback,
    and timestamp even when no request or user_id is provided."""
    logger = MagicMock(spec=structlog.stdlib.BoundLogger)
    exc = ValueError("something broke")

    log_exception(logger, exc, event="test_event")

    logger.error.assert_called_once()
    call_args = logger.error.call_args
    assert call_args[0][0] == "test_event"
    context = call_args[1]
    assert context["exception_type"] == "ValueError"
    assert context["exception_message"] == "something broke"
    assert "traceback" in context
    assert "Timestamp" in context["timestamp"] or context["timestamp"].endswith("Z")


def test_log_exception_with_request() -> None:
    """When a request object is provided, request_id, method, path, and
    client_ip must be included."""
    logger = MagicMock(spec=structlog.stdlib.BoundLogger)
    exc = RuntimeError("req error")
    request = FakeRequest(method="POST", path="/api/v1/recommend/trending", host="10.0.0.1")

    log_exception(logger, exc, event="req_failure", request=request)

    context = logger.error.call_args[1]
    assert context["request_id"] == "test-request-id"
    assert context["method"] == "POST"
    assert context["path"] == "/api/v1/recommend/trending"
    assert context["client_ip"] == "10.0.0.1"


def test_log_exception_with_user_id() -> None:
    """When a user_id is provided, it must appear in the log entry."""
    logger = MagicMock(spec=structlog.stdlib.BoundLogger)
    exc = PermissionError("access denied")

    log_exception(logger, exc, event="auth_failure", user_id="user_abc_42")

    context = logger.error.call_args[1]
    assert context["user_id"] == "user_abc_42"


def test_log_exception_with_extra_fields() -> None:
    """Extra keyword arguments must be forwarded to the log entry."""
    logger = MagicMock(spec=structlog.stdlib.BoundLogger)
    exc = KeyError("missing_key")

    log_exception(
        logger,
        exc,
        event="cache_error",
        cache_key="movies:trending",
        redis_host="localhost",
    )

    context = logger.error.call_args[1]
    assert context["cache_key"] == "movies:trending"
    assert context["redis_host"] == "localhost"


def test_log_exception_with_request_and_user() -> None:
    """All fields (request context + user_id + extra) must coexist."""
    logger = MagicMock(spec=structlog.stdlib.BoundLogger)
    exc = ConnectionError("timeout")
    request = FakeRequest(method="GET", path="/api/v1/search/semantic", host="192.168.1.1")

    log_exception(
        logger,
        exc,
        event="db_timeout",
        request=request,
        user_id="dev_user_123",
        db_name="postgres_main",
    )

    context = logger.error.call_args[1]
    assert context["exception_type"] == "ConnectionError"
    assert context["exception_message"] == "timeout"
    assert context["request_id"] == "test-request-id"
    assert context["method"] == "GET"
    assert context["path"] == "/api/v1/search/semantic"
    assert context["client_ip"] == "192.168.1.1"
    assert context["user_id"] == "dev_user_123"
    assert context["db_name"] == "postgres_main"


def test_log_exception_traceback_includes_call_stack() -> None:
    """The traceback field must contain the call stack, not just a message."""
    logger = MagicMock(spec=structlog.stdlib.BoundLogger)

    def inner():
        raise ValueError("nested error")

    try:
        inner()
    except ValueError as exc:
        log_exception(logger, exc, event="nested_failure")

    context = logger.error.call_args[1]
    trace = context["traceback"]
    assert "ValueError" in trace
    assert "nested error" in trace
    assert "inner" in trace


def test_log_exception_request_no_client() -> None:
    """When the request has no client (e.g. during testing), client_ip must
    be None rather than crashing."""
    logger = MagicMock(spec=structlog.stdlib.BoundLogger)
    exc = Exception("no client")
    request = FakeRequest()
    request.client = None

    log_exception(logger, exc, event="no_client_case", request=request)

    context = logger.error.call_args[1]
    assert context["client_ip"] is None


def test_log_exception_timestamp_is_isoformat() -> None:
    """The timestamp must be a valid ISO-8601 formatted string."""
    logger = MagicMock(spec=structlog.stdlib.BoundLogger)
    exc = Exception("timestamp test")

    log_exception(logger, exc, event="ts_test")

    context = logger.error.call_args[1]
    ts = context["timestamp"]
    assert "T" in ts
    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    assert isinstance(parsed, datetime)


def test_log_exception_request_id_fallback() -> None:
    """If request.state has no request_id, the helper should not crash."""
    logger = MagicMock(spec=structlog.stdlib.BoundLogger)
    exc = Exception("no request_id")
    request = FakeRequest()
    del request.state.request_id

    log_exception(logger, exc, event="no_req_id", request=request)

    context = logger.error.call_args[1]
    assert context["request_id"] is None


def test_log_exception_preserves_logger_type() -> None:
    """The helper must accept a real structlog logger without crashing."""
    exc = ValueError("real logger test")
    log_exception(structlog.get_logger(), exc, event="real_logger_test")
