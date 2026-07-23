from contextlib import asynccontextmanager
import time
import uuid

import structlog
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import datetime
import structlog.contextvars

from app.api.v1 import api_router
from app.core.config import settings
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter
logger = structlog.get_logger()

HEALTH_ERROR_PREFIX = "error:"


def get_request_id(request: Request) -> str:
    """Return the request's correlation ID, generating one only as a fallback."""
    return getattr(request.state, "request_id", str(uuid.uuid4()))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("cineiq_starting", host=settings.backend_host, port=settings.backend_port)
    if not settings.clerk_secret_key or "REPLACE" in settings.clerk_secret_key:
        if settings.environment == "development":
            logger.warning(
                "auth_bypass_active",
                message="Clerk secret key is missing or default. Authentication bypass is active in development mode."
            )

    # --- Configure Google Gemini ONCE at startup (not per request) ---
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

    yield
    # Shutdown
    logger.info("cineiq_stopped")

app = FastAPI(
    title="CINEIQ API",
    description="AI-Powered Movie Recommendations and Social Discovery",
    version="1.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Generate a unique correlation ID for every incoming request.
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

    # Expose the correlation ID to clients for support/debugging.
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
        detail=exc.detail,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": "HTTP_ERROR",
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = get_request_id(request)
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        traceback=traceback.format_exc(),
        request_id=request_id,
    )
    if settings.environment.lower() in ("production", "prod"):
        detail = "Internal server error"
    else:
        detail = f"{type(exc).__name__}: {exc}"
    return JSONResponse(
        status_code=500,
        content={
            "detail": detail,
            "error_code": "INTERNAL_SERVER_ERROR",
            "request_id": request_id,
        },
    )

@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    request_id = get_request_id(request)
    response = JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please try again later.",
            "error_code": "RATE_LIMIT_EXCEEDED",
            "request_id": request_id,
        },
    )
    if hasattr(request.app.state, "limiter"):
        response = request.app.state.limiter._route_manager.headers_handler(response)
    return response

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
@limiter.exempt
async def health_check():
    # Single UTC timestamp used for every service in this request.
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
    # Check Gemini API
    gemini_status = "configured" if settings.gemini_api_key else "not_configured"

    checks = {
        "redis": {"status": redis_status, "last_checked": last_checked},
        "postgres": {"status": postgres_status, "last_checked": last_checked},
        "gemini_api": {"status": gemini_status, "last_checked": last_checked},
    }

    # Define required services that must be configured and operational for "healthy"
    required_services = {"redis", "postgres", "gemini_api"}

    # Determine if any required service is not configured
    any_required_not_configured = any(
        service in required_services and v["status"] == "not_configured"
        for service, v in checks.items()
    )

    # Determine if any required service has an error
    any_required_error = any(
        service in required_services
        and v["status"].startswith(HEALTH_ERROR_PREFIX)
        for service, v in checks.items()
    )

    if any_required_not_configured:
        overall_status = "not_configured"
    elif any_required_error:
        overall_status = "degraded"
    else:
        # All required services are ok/configured; check optional services
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
