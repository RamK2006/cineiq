import structlog
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.core.logging import log_exception

logger = structlog.get_logger()

# ─── Redis Setup (Upstash) ───
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
                log_exception(logger, e, event="upstash_redis_init_failed")
    return _redis_client


# ─── SQLAlchemy Async Database Setup ───
_db_url = settings.resolved_database_url

# SQLite requires connect_args to allow multi-threaded access
_connect_args = {}
if "sqlite" in _db_url:
    _connect_args["check_same_thread"] = False

engine = create_async_engine(
    _db_url,
    pool_pre_ping=True,
    echo=False,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    """Dependency for getting async SQLAlchemy database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
