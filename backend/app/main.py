from contextlib import asynccontextmanager
import traceback
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import structlog.contextvars

from app.core.config import settings

logger = structlog.get_logger()


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

from app.api.v1 import api_router
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    checks = {}
    
    # Check Redis
    try:
        from app.db.session import get_redis
        redis = get_redis()
        if redis:
            redis.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "not_configured"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:100]}"
        
    # Check Gemini API
    checks["gemini_api"] = "configured" if settings.gemini_api_key else "not_configured"
    
    all_ok = all(v in ("ok", "configured", "not_configured") for v in checks.values())
    
    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": checks
    }
