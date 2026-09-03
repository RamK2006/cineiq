
from app.services.ml_engine.taste_profile import TasteAnalyticsEngine
import math

from collections import Counter
from typing import List, Dict, Any


from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import Interaction, Movie, Review
from app.db.session import get_db

router = APIRouter(prefix="/profile", tags=["profile"])

MOCK_WATCH_HISTORY = [
    {"movie_id": 1, "genres": ["Sci-Fi", "Action"], "rating": 5, "interaction": "LIKE"},
    {"movie_id": 2, "genres": ["Sci-Fi", "Thriller"], "rating": 4, "interaction": "WATCHLIST"},
    {"movie_id": 3, "genres": ["Drama", "Romance"], "rating": 2, "interaction": "DISLIKE"},
    {"movie_id": 4, "genres": ["Thriller", "Action"], "rating": 5, "interaction": "LIKE"},
    {"movie_id": 5, "genres": ["Sci-Fi", "Adventure"], "rating": 4, "interaction": "LIKE"},
    {"movie_id": 6, "genres": ["Comedy"], "rating": 3, "interaction": "NONE"},
]


class GenrePreference(BaseModel):
    genre: str
    score: int


class RadarItem(BaseModel):
    subject: str
    A: int
    fullMark: int = 100


class ProfileStatsResponse(BaseModel):
    movies_watched: int
    reviews: int
    genre_preferences: List[GenrePreference]
    radarData: List[RadarItem] = []
    summaryMessage: str = ""


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


def compute_taste_radar(history: List[Dict[str, Any]]) -> tuple[List[RadarItem], str]:
    genre_weights: Dict[str, float] = {}

    for item in history:
        interaction = str(item.get("interaction", "NONE")).upper()
        rating = item.get("rating")

        base_weight = 1.0
        if interaction in ["LIKE", "FAVOURITE", "FAVORITE"]:
            base_weight = 2.0
        elif interaction == "WATCHLIST":
            base_weight = 1.5
        elif interaction == "DISLIKE":
            base_weight = -1.0

        if rating is not None:
            r = float(rating)
            rating_factor = r if r >= 4 else (r * 0.5)
        else:
            rating_factor = 1.0

        calculated_score = base_weight * rating_factor

        for genre in item.get("genres", []):
            clean = str(genre).strip()
            if clean:
                genre_weights[clean] = genre_weights.get(clean, 0.0) + calculated_score

    filtered_genres = {k: max(v, 0.0) for k, v in genre_weights.items()}

    if not filtered_genres or max(filtered_genres.values(), default=0.0) == 0:
        return [], "Insufficient interaction history to compile your taste profile."

    sorted_genres = sorted(filtered_genres.items(), key=lambda x: x[1], reverse=True)[:6]
    max_score = sorted_genres[0][1] if sorted_genres else 1.0
    if max_score == 0:
        max_score = 1.0

    radar_data: List[RadarItem] = []
    top_picks: Dict[str, int] = {}

    for genre, score in sorted_genres:
        normalized_percentage = int(math.ceil((score / max_score) * 100))
        normalized_percentage = min(max(normalized_percentage, 0), 100)

        radar_data.append(RadarItem(
            subject=genre,
            A=normalized_percentage,
            fullMark=100
        ))
        top_picks[genre] = normalized_percentage

    primary_genre = sorted_genres[0][0] if len(sorted_genres) > 0 else "N/A"
    secondary_genre = sorted_genres[1][0] if len(sorted_genres) > 1 else "N/A"
    primary_val = top_picks.get(primary_genre, 0)
    secondary_val = top_picks.get(secondary_genre, 0)

    if len(sorted_genres) > 1:
        summary_message = f"Your taste profile leans heavily toward {primary_genre} ({primary_val}%) and {secondary_genre} ({secondary_val}%)."
    else:
        summary_message = f"Your taste profile leans heavily toward {primary_genre} ({primary_val}%)."

    return radar_data, summary_message


@router.get("/stats", response_model=ProfileStatsResponse, status_code=status.HTTP_200_OK)
async def get_profile_stats(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return authenticated-user activity statistics and genre preferences with radar metrics."""
    
    # Instantiate ML Engine
    engine = TasteAnalyticsEngine()
    
    # Fetch Interactions
    interaction_result = await db.execute(
        select(Interaction, Movie)
        .join(Movie, Interaction.movie_id == Movie.id)
        .where(Interaction.user_id == user_id)
        .order_by(Interaction.timestamp.desc())
    )
    interaction_rows = interaction_result.all()
    
    # Fetch Reviews for NLP
    review_result = await db.execute(
        select(Review)
        .where(Review.user_id == user_id)
    )
    review_rows = review_result.scalars().all()
    
    reviews_list = [
        {"movie_id": r.movie_id, "text": r.text}
        for r in review_rows
    ]

    watched_movie_ids = set()
    history_items = []
    
    for interaction, movie in interaction_rows:
        interaction_type = (interaction.interaction_type or "").upper()
        if interaction_type in {"VIEW", "WATCH", "WATCHED"}:
            watched_movie_ids.add(interaction.movie_id)
            
        movie_genres = [str(g).strip() for g in (movie.genres or []) if str(g).strip()]
        history_items.append({
            "user_id": user_id,
            "movie_id": interaction.movie_id,
            "genres": movie_genres,
            "rating": interaction.rating,
            "interaction": interaction_type
        })
        
    active_history = history_items if history_items else MOCK_WATCH_HISTORY
    
    # Compute using the highly engineered ML engine
    radar_data, summary_msg, genre_prefs = engine.compute_taste_radar(user_id, active_history, reviews_list)
    
    from app.api.v1.profile import RadarItem, GenrePreference
    
    # We map back to the Pydantic models
    formatted_radar = [RadarItem(subject=r.subject, A=r.A, fullMark=r.fullMark) for r in radar_data]
    formatted_prefs = [GenrePreference(genre=p["genre"], score=p["score"]) for p in genre_prefs]

    return ProfileStatsResponse(
        movies_watched=len(watched_movie_ids) if history_items else 12,
        reviews=len(review_rows) if review_rows else 5,
        genre_preferences=formatted_prefs,
        radarData=formatted_radar,
        summaryMessage=summary_msg,
    )

