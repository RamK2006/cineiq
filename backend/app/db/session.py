import structlog
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

logger = structlog.get_logger()

# ─── Redis Setup (Upstash) ───
_redis_client = None
_engine = None
_async_session_local = None


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



def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


def _get_session_local():
    global _async_session_local
    if _async_session_local is None:
        _async_session_local = async_sessionmaker(
            _get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_local


async def get_db():
    """Dependency for getting async SQLAlchemy session."""
    async with _get_session_local()() as session:
        yield session

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
