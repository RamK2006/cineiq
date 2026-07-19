from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

# Determine storage backend
storage_uri = "memory://"
storage_options = {}

if settings.rate_limit_enabled:
    if settings.upstash_redis_url and settings.upstash_redis_token:
        try:
            # Import to trigger custom storage registration with limits
            from app.core.rate_limit_storage import UpstashRedisStorage  # noqa: F401
            storage_uri = "upstash://"
        except Exception as e:
            import logging

            logging.getLogger("uvicorn").warning(
                f"Failed to initialize Upstash Redis rate limit storage, falling back to memory: {e}"
            )

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    storage_options=storage_options,
    default_limits=[settings.rate_limit_global],
    enabled=settings.rate_limit_enabled,
    headers_enabled=True,  # X-RateLimit-* headers
)
