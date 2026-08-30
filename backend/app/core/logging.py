import traceback
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from fastapi import Request

logger = structlog.get_logger()


def log_exception(
    bound_logger: Any,
    exc: Exception,
    event: str = "exception_occurred",
    request: Optional[Request] = None,
    user_id: Optional[str] = None,
    **kwargs: Any,
) -> None:
    """Log an exception with consistent structured context.

    Captures exception type, message, formatted traceback, ISO timestamp,
    request details (when available), authenticated user ID, and any
    additional caller-supplied contextual kwargs.
    """
    now = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    tb_str = "".join(
        traceback.format_exception(
            type(exc),
            exc,
            exc.__traceback__,
        )
    )

    context: dict[str, Any] = {
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "traceback": tb_str,
        "timestamp": now,
    }

    if request is not None:
        context["request_id"] = getattr(
            getattr(request, "state", None),
            "request_id",
            None,
        )
        context["method"] = getattr(request, "method", None)
        url = getattr(request, "url", None)
        context["path"] = getattr(url, "path", None) if url else None
        client = getattr(request, "client", None)
        context["client_ip"] = getattr(client, "host", None) if client else None

    if user_id is not None:
        context["user_id"] = user_id

    # Merge any additional contextual arguments
    context.update(kwargs)

    bound_logger.error(event, **context)
