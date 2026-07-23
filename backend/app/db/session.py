import structlog
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

logger = structlog.get_logger()

_redis_client = None


def get_redis():
    """Get or create Upstash Redis client."""
    global _redis_client
    if _redis_client is None:
        if settings.upstash_redis_url and settings.upstash_redis_token:
            try:
                from upstash_redis import Redis

                _redis_client = Redis(
                    url=settings.upstash_redis_url,
                    token=settings.upstash_redis_token,
                )
            except Exception as e:
                logger.warning("upstash_redis_init_failed", error=str(e))
    return _redis_client

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    """Dependency for getting async SQLAlchemy session."""
    async with AsyncSessionLocal() as session:
        yield session
