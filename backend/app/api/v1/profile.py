from collections import Counter
from typing import List, Literal, Optional
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import Interaction, Movie, User
from app.db.session import get_db
from app.api.v1.recommend import MovieItem, _calculate_match_score

router = APIRouter(prefix="/profile", tags=["profile"])


class GenrePreference(BaseModel):
    genre: str
    score: int


class ProfileStatsResponse(BaseModel):
    movies_watched: int
    reviews: int
    genre_preferences: List[GenrePreference]


class InteractionCreate(BaseModel):
    movie_id: str
    interaction_type: Literal["WATCHLIST", "WATCHED", "LIKED", "watchlist", "watched", "liked"]


class PaginatedMoviesResponse(BaseModel):
    items: List[MovieItem]
    page: int
    limit: int
    total: int
    pages: int


def _normalise_preferences(counter: Counter[str]) -> List[GenrePreference]:
    if not counter:
        return []

    highest = max(counter.values())
    return [
        GenrePreference(
            genre=genre,
            score=max(1, round((weight / highest) * 100)),
        )
        for genre, weight in counter.most_common(6)
    ]


@router.get("/stats", response_model=ProfileStatsResponse)
async def get_profile_stats(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return authenticated-user activity statistics and genre preferences."""
    result = await db.execute(
        select(Interaction, Movie)
        .join(Movie, Interaction.movie_id == Movie.id)
        .where(Interaction.user_id == user_id)
        .order_by(Interaction.timestamp.desc())
    )
    rows = result.all()

    watched_movie_ids = set()
    review_count = 0
    genre_weights: Counter[str] = Counter()

    for interaction, movie in rows:
        interaction_type = (interaction.interaction_type or "").lower()

        if interaction_type in {"view", "watch", "watched"}:
            watched_movie_ids.add(interaction.movie_id)

        if interaction.rating is not None or interaction_type == "review":
            review_count += 1

        weight = 1
        if interaction_type in {"like", "liked", "favourite", "favorite", "watchlist"}:
            weight = 2
        if interaction.rating is not None:
            weight = max(weight, max(1, round(float(interaction.rating))))

        for genre in movie.genres or []:
            clean_genre = str(genre).strip()
            if clean_genre:
                genre_weights[clean_genre] += weight

    return ProfileStatsResponse(
        movies_watched=len(watched_movie_ids),
        reviews=review_count,
        genre_preferences=_normalise_preferences(genre_weights),
    )


@router.post("/interactions", status_code=status.HTTP_201_CREATED)
async def create_interaction(
    payload: InteractionCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a user-movie interaction (WATCHLIST, WATCHED, LIKED)."""
    # Ensure user exists in database
    user = await db.get(User, user_id)
    if user is None:
        user = User(id=user_id)
        db.add(user)
        await db.flush()

    # Ensure movie exists in database
    movie = await db.get(Movie, payload.movie_id)
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie is not in the catalogue")

    normalized_type = payload.interaction_type.lower()

    # Check if this interaction already exists
    stmt = select(Interaction).where(
        Interaction.user_id == user_id,
        Interaction.movie_id == payload.movie_id,
        Interaction.interaction_type == normalized_type,
    )
    result = await db.execute(stmt)
    interaction = result.scalars().first()

    if interaction:
        interaction.timestamp = datetime.now(timezone.utc)
    else:
        interaction = Interaction(
            user_id=user_id,
            movie_id=payload.movie_id,
            interaction_type=normalized_type,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(interaction)

    await db.commit()
    await db.refresh(interaction)

    return {
        "id": interaction.id,
        "user_id": interaction.user_id,
        "movie_id": interaction.movie_id,
        "interaction_type": interaction.interaction_type.upper(),
        "timestamp": interaction.timestamp,
    }


@router.delete("/interactions/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interaction(
    movie_id: str,
    type: Optional[str] = Query(default=None, description="Interaction type to remove"),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user-movie interaction. If type is provided, remove only that type."""
    stmt = delete(Interaction).where(
        Interaction.user_id == user_id,
        Interaction.movie_id == movie_id,
    )
    if type:
        stmt = stmt.where(Interaction.interaction_type == type.lower())

    await db.execute(stmt)
    await db.commit()


@router.get("/interactions", response_model=PaginatedMoviesResponse)
async def get_interactions(
    type: str = Query(..., description="Interaction type: WATCHLIST, WATCHED, or LIKED"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve paginated movies associated with a user interaction type."""
    normalized_type = type.lower()

    # Get total count
    count_stmt = (
        select(func.count(Interaction.id))
        .where(
            Interaction.user_id == user_id,
            Interaction.interaction_type == normalized_type,
        )
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # Get paginated movies
    stmt = (
        select(Movie)
        .join(Interaction, Movie.id == Interaction.movie_id)
        .where(
            Interaction.user_id == user_id,
            Interaction.interaction_type == normalized_type,
        )
        .order_by(Interaction.timestamp.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(stmt)
    movies = result.scalars().all()

    items = []
    for movie in movies:
        match_score = _calculate_match_score(movie.vote_average, movie.popularity)
        items.append(
            MovieItem(
                id=movie.id,
                title=movie.title,
                poster_path=movie.poster_path,
                vote_average=movie.vote_average,
                genres=movie.genres or [],
                match_score=match_score,
            )
        )

    pages = math.ceil(total / limit) if total > 0 else 0

    return PaginatedMoviesResponse(
        items=items,
        page=page,
        limit=limit,
        total=total,
        pages=pages,
    )

