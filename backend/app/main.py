"""
backend/app/main.py
-------------------
Main entry point for the CINEIQ API application, incorporating FastAPI setup,
lifespan management, middleware configurations, error handlers, and health endpoints.
"""

from __future__ import annotations

import datetime
from contextlib import asynccontextmanager
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import event
import structlog
import structlog.contextvars
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import api_router
from app.api.v1.room import room_websocket_signaling_endpoint
from app.core.config import settings
from app.core.logging import log_exception
from app.core.metrics import (
    db_query_duration_seconds,
    http_request_duration_seconds,
    http_requests_total,
)
from app.core.rate_limit import limiter
from app.core.security import ALLOWED_ORIGINS, CSP_DIRECTIVES, ENV
from app.db.models import Base
from app.db.session import AsyncSessionLocal, engine
from app.services.sync import seed_movies_if_empty

try:
    from prometheus_fastapi_instrumentator import Instrumentator
except ImportError:
    Instrumentator = None

HEALTH_ERROR_PREFIX = "error:"

logger = structlog.get_logger(__name__)


def get_request_id(request: Request) -> str:
    """Return the request's correlation ID, generating one only as a fallback."""
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Return the shared HTTP client from application state."""
    return request.app.state.http_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle events."""
    # Startup Initialization
    logger.info("cineiq_starting", host=settings.backend_host, port=settings.backend_port)
    
    # Initialize shared HTTP client
    try:
        app.state.http_client = httpx.AsyncClient(timeout=10.0)
        logger.info("shared_httpx_client_created", timeout_seconds=10.0)
    except Exception as e:
        logger.error("httpx_client_creation_failed", error=str(e))
        app.state.http_client = None

    # Initialize Database & Seeding
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database_tables_created")

        async with AsyncSessionLocal() as db:
            await seed_movies_if_empty(db)
    except Exception as e:
        logger.error("database_startup_failed", error=str(e))

    if not settings.clerk_secret_key or "REPLACE" in settings.clerk_secret_key:
        logger.warning(
            "clerk_not_configured",
            message="Protected endpoints will return 503 until Clerk is configured.",
        )

    # Configure Google Gemini
    if settings.gemini_api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            logger.info("gemini_configured", model=settings.gemini_model)
        except Exception as e:
            logger.error("gemini_configuration_failed", error=str(e))
    else:
        logger.warning(
            "gemini_not_configured",
            message="GEMINI_API_KEY is not set; keyword extraction will be skipped.",
        )

    # Initialize TMDB Genre map
    try:
        from app.api.v1.recommend import initialize_tmdb_genres
        if app.state.http_client:
            await initialize_tmdb_genres(app.state.http_client)
    except Exception as e:
        logger.error("tmdb_genre_initialization_failed", error=str(e))

    yield

    # Shutdown Cleanup
    logger.info("cineiq_stopped")
    if getattr(app.state, "http_client", None) is not None:
        try:
            await app.state.http_client.aclose()
            logger.info("shared_httpx_client_closed")
        except Exception as e:
            logger.error("httpx_client_close_failed", error=str(e))

    await engine.dispose()


app = FastAPI(
    title="CINEIQ API",
    description="AI-Powered Movie Recommendations and Social Discovery",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure Rate Limiting Middleware
try:
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
except Exception as rl_err:
    logger.warning("slowapi_middleware_disabled", error=str(rl_err))

# Enforce strict CORS whitelist validation
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)


# Custom Security Headers Middleware for OWASP Compliance
@app.middleware("http")
async def add_security_headers_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    response: Response = await call_next(request)

    response.headers["Content-Security-Policy"] = CSP_DIRECTIVES
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    if ENV in ("production", "prod"):
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

    return response


# Metrics Collection Middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    http_requests_total.labels(
        method=request.method, path=request.url.path, status=response.status_code
    ).inc()

    http_request_duration_seconds.labels(
        method=request.method, path=request.url.path
    ).observe(duration)

    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start = time.time()
    response = await call_next(request)
    latency = int((time.time() - start) * 1000)

    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=latency,
        request_id=request_id,
    )

    response.headers["X-Request-ID"] = request_id
    structlog.contextvars.clear_contextvars()
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = get_request_id(request)
    logger.warning(
        "request_validation_error",
        path=request.url.path,
        errors=exc.errors(),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "error_code": "VALIDATION_ERROR",
            "request_id": request_id,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = get_request_id(request)
    logger.warning(
        "http_exception",
        path=request.url.path,
        status_code=exc.status_code,
        detail=getattr(exc, "detail", str(exc)),
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": getattr(exc, "detail", str(exc)),
            "error_code": "HTTP_ERROR",
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = get_request_id(request)
    log_exception(logger, exc, event="unhandled_exception", request=request)
    
    detail = "Internal server error" if ENV in ("production", "prod") else f"{type(exc).__name__}: {exc}"
    return JSONResponse(
        status_code=500,
        content={
            "detail": detail,
            "error_code": "INTERNAL_SERVER_ERROR",
            "request_id": request_id,
        },
    )


try:
    @app.exception_handler(RateLimitExceeded)
    async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
        request_id = get_request_id(request)
        retry_after = "60"
        if hasattr(exc, "retry_after") and exc.retry_after is not None:
            retry_after = str(int(exc.retry_after))

        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests. Please try again later.",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "request_id": request_id,
            },
            headers={"Retry-After": retry_after},
        )
except Exception:
    pass

# Include Routers & WebSockets
app.include_router(api_router, prefix="/api/v1")


# Wrapped WebSocket endpoint with active client connection gauge instrumentation
@app.websocket("/ws/room/{room_id}/{user_id}")
async def instrumented_websocket_endpoint(websocket, room_id: str, user_id: str):
    websocket_connected_clients.inc()
    try:
        await room_websocket_signaling_endpoint(websocket, room_id, user_id)
    finally:
        websocket_connected_clients.dec()


# Database query event instrumentation
@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if hasattr(context, "_query_start_time"):
        duration = time.time() - context._query_start_time
        db_query_duration_seconds.observe(duration)


# Prometheus instrumentator setup
if Instrumentator:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health")
async def health_check():
    last_checked = (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    # Check Redis
    try:
        from app.db.session import get_redis
        redis = get_redis()
        if redis:
            redis.ping()
            redis_status = "ok"
        else:
            redis_status = "not_configured"
    except Exception as e:
        redis_status = f"{HEALTH_ERROR_PREFIX}{str(e)[:100]}"

    # Check Postgres
    try:
        from app.db.session import engine
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        postgres_status = "ok"
    except Exception as e:
        postgres_status = f"{HEALTH_ERROR_PREFIX}{str(e)[:100]}"

    gemini_status = "configured" if settings.gemini_api_key else "not_configured"

    checks = {
        "redis": {"status": redis_status, "last_checked": last_checked},
        "postgres": {"status": postgres_status, "last_checked": last_checked},
        "gemini_api": {"status": gemini_status, "last_checked": last_checked},
    }

    required_services = {"redis", "postgres", "gemini_api"}

    any_required_not_configured = any(
        service in required_services and v["status"] == "not_configured"
        for service, v in checks.items()
    )

    any_required_error = any(
        service in required_services and v["status"].startswith(HEALTH_ERROR_PREFIX)
        for service, v in checks.items()
    )

    if any_required_not_configured:
        overall_status = "not_configured"
    elif any_required_error:
        overall_status = "degraded"
    else:
        any_optional_error = any(
            service not in required_services
            and v["status"].startswith(HEALTH_ERROR_PREFIX)
            for service, v in checks.items()
        )
        overall_status = "degraded" if any_optional_error else "healthy"

    status_code = 503 if overall_status == "not_configured" else 200

    return JSONResponse(
        status_code=status_code,
        content={"status": overall_status, "checks": checks},
    )
