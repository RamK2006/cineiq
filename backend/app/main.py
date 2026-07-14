from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import datetime
import structlog

from app.core.config import settings

logger = structlog.get_logger()

HEALTH_ERROR_PREFIX = "error:"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("cineiq_starting", host=settings.backend_host, port=settings.backend_port)
    yield
    # Shutdown
    logger.info("cineiq_stopped")

app = FastAPI(
    title="CINEIQ API",
    description="AI-Powered Movie Recommendations and Social Discovery",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    latency = int((time.time() - start) * 1000)
    
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=latency
    )
    
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

from app.api.v1 import api_router
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
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

    # Check Gemini API
    gemini_status = "configured" if settings.gemini_api_key else "not_configured"

    checks = {
        "redis": {"status": redis_status, "last_checked": last_checked},
        "gemini_api": {"status": gemini_status, "last_checked": last_checked},
    }

    # Define required services that must be configured and operational for "healthy"
    required_services = {"redis", "gemini_api"}

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
