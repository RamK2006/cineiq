from datetime import datetime, timedelta, timezone
from typing import List, Optional
import structlog
from pydantic import BaseModel, Field
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.future import select
from sqlalchemy import func, case
from sqlalchemy.ext.asyncio import AsyncSession


from app.db.session import get_db, get_redis
from app.db.models import Interaction, Movie

logger = structlog.get_logger()
router = APIRouter(prefix="/analytics", tags=["analytics"])


class AnalyticsEventRequest(BaseModel):
    event_type: str = Field(..., description="Interaction event type: view, click, trailer_play")
    movie_id: str = Field(..., description="Target movie ID")
    source: Optional[str] = Field("recommended", description="Source of interaction: trending, search, recommended")
    user_id: Optional[str] = Field(None, description="Optional user ID")


class AnalyticsEventResponse(BaseModel):
    status: str
    event_type: str
    movie_id: str


class TopClickedMovieItem(BaseModel):
    movie_id: str
    title: str
    poster_path: Optional[str] = None
    clicks: int
    views: int
    ctr: float


class TopClickedResponse(BaseModel):
    timeframe: str
    movies: List[TopClickedMovieItem]


async def _record_event_background(
    event_type: str,
    movie_id: str,
    source: str,
    user_id: Optional[str],
):
    """Asynchronously buffer event in Redis and save to database."""
    logger.info("analytics_event_received", event_type=event_type, movie_id=movie_id, source=source)

    # 1. Update Redis counters if Redis is configured
    redis = get_redis()
    if redis:
        try:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            redis.incr(f"analytics:{event_type}:{movie_id}:{today_str}")
            redis.expire(f"analytics:{event_type}:{movie_id}:{today_str}", 86400 * 7)
        except Exception as e:
            logger.warning("redis_analytics_incr_failed", error=str(e))

    # 2. Persist to database session
    try:
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            interaction = Interaction(
                user_id=user_id,
                movie_id=movie_id,
                interaction_type=event_type,
            )
            db.add(interaction)
            await db.commit()
            logger.info("analytics_event_persisted", event_type=event_type, movie_id=movie_id)
    except Exception as e:
        logger.error("analytics_db_persist_failed", error=str(e))


@router.post("/event", response_model=AnalyticsEventResponse)
async def track_event(
    event: AnalyticsEventRequest,
    background_tasks: BackgroundTasks,
):
    """
    Record lightweight telemetry interaction events (view, click, trailer_play).
    Processed asynchronously via BackgroundTasks to guarantee zero latency impact on navigation.
    """
    valid_types = {"view", "click", "trailer_play"}
    if event.event_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event_type. Must be one of: {', '.join(valid_types)}"
        )

    background_tasks.add_task(
        _record_event_background,
        event.event_type,
        event.movie_id,
        event.source or "recommended",
        event.user_id,
    )

    return AnalyticsEventResponse(
        status="queued",
        event_type=event.event_type,
        movie_id=event.movie_id,
    )


@router.get("/top-clicked", response_model=TopClickedResponse)
async def get_top_clicked_movies(
    hours: int = Query(24, ge=1, le=168, description="Timeframe window in hours"),
    limit: int = Query(10, ge=1, le=50, description="Max movies to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get top clicked movies over the past timeframe (default 24h) along with CTR statistics.
    """
    since_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    try:
        click_case = case((Interaction.interaction_type == "click", 1), else_=0)
        view_case = case((Interaction.interaction_type == "view", 1), else_=0)

        stmt = (
            select(
                Interaction.movie_id,
                func.count(Interaction.id).label("total_interactions"),
                func.sum(click_case).label("click_count"),
                func.sum(view_case).label("view_count"),
            )
            .where(Interaction.timestamp >= since_time)
            .group_by(Interaction.movie_id)
            .order_by(func.sum(click_case).desc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            # Fallback: Query popular movies from Movie table
            movie_stmt = select(Movie).order_by(Movie.popularity.desc()).limit(limit)
            movie_res = await db.execute(movie_stmt)
            fallback_movies = movie_res.scalars().all()
            
            top_movies = [
                TopClickedMovieItem(
                    movie_id=m.id,
                    title=m.title,
                    poster_path=m.poster_path,
                    clicks=int(m.popularity / 10),
                    views=int(m.popularity),
                    ctr=round(min((m.popularity / 10) / max(m.popularity, 1.0), 1.0), 2),
                )
                for m in fallback_movies
            ]
            return TopClickedResponse(timeframe=f"{hours}h", movies=top_movies)

        movie_ids = [row.movie_id for row in rows]
        movie_query = select(Movie).where(Movie.id.in_(movie_ids))
        movie_res = await db.execute(movie_query)
        movie_map = {m.id: m for m in movie_res.scalars().all()}

        top_movies = []
        for row in rows:
            m_id = row.movie_id
            clicks = int(row.click_count or 0)
            views = int(row.view_count or 0)
            ctr = round(clicks / max(views, 1), 2) if views > 0 else round(clicks / max(clicks, 1), 2)
            
            m_obj = movie_map.get(m_id)
            title = m_obj.title if m_obj else f"Movie {m_id}"
            poster_path = m_obj.poster_path if m_obj else None

            top_movies.append(
                TopClickedMovieItem(
                    movie_id=m_id,
                    title=title,
                    poster_path=poster_path,
                    clicks=clicks,
                    views=views,
                    ctr=ctr,
                )
            )

        return TopClickedResponse(timeframe=f"{hours}h", movies=top_movies)

    except Exception as e:
        logger.error("get_top_clicked_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve top clicked analytics metrics",
        )
