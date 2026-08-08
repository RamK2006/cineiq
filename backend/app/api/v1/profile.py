from collections import Counter
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import Interaction, Movie
from app.db.session import get_db

router = APIRouter(prefix="/profile", tags=["profile"])


class GenrePreference(BaseModel):
    genre: str
    score: int


class ProfileStatsResponse(BaseModel):
    movies_watched: int
    reviews: int
    genre_preferences: List[GenrePreference]


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
        if interaction_type in {"like", "favourite", "favorite", "watchlist"}:
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
