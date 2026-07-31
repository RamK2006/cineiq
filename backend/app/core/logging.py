"""Lightweight helpers for structured exception logging with request context.

This module does NOT configure logging — it reuses the existing structlog
setup installed by the application.  Every function here accepts a logger
instance so callers can continue using their own ``structlog.get_logger()``.
"""

from datetime import datetime, timezone
from typing import Any, Optional

import structlog
import traceback

from fastapi import Request


def log_exception(
    logger: structlog.stdlib.BoundLogger,
    exc: Exception,
    event: str = "unhandled_exception",
    request: Optional[Request] = None,
    user_id: Optional[str] = None,
    **extra: Any,
) -> None:
    """Log an exception with full request context and structured fields.

    The caller's *logger* instance is used directly so that the application's
    existing structlog configuration (processors, renderers, etc.) is
    preserved.  Request context is extracted from the FastAPI ``Request``
    object when available.

    Parameters
    ----------
    logger:
        A structlog logger obtained via ``structlog.get_logger()``.
    exc:
        The exception that was caught.
    event:
        A short, descriptive event name (default ``"unhandled_exception"``).
    request:
        The FastAPI ``Request`` object, if available in the calling scope.
        When provided, request_id, method, path, and client IP are
        automatically included in the structured log entry.
    user_id:
        The authenticated user identifier, if available.
    **extra:
        Any additional key-value pairs to include in the log entry.
    """
    now = datetime.now(timezone.utc).isoformat()

    context: dict[str, Any] = {
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "traceback": traceback.format_exc(),
        "timestamp": now,
    }

    if request is not None:
        context["request_id"] = getattr(request.state, "request_id", None)
        context["method"] = request.method
        context["path"] = request.url.path
        context["client_ip"] = (
            request.client.host if request.client else None
        )

    if user_id is not None:
        context["user_id"] = user_id

    context.update(extra)
    logger.error(event, **context)