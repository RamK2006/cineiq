from typing import Dict, List, Optional
from pydantic import BaseModel
import hashlib
import httpx
import json
import os
import pickle
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_redis, get_db
from app.db.models import Movie

logger = structlog.get_logger()
router = APIRouter(prefix="/recommend", tags=["recommendation"])

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_GENRE_CACHE_KEY = "tmdb:genres:movie"
TMDB_GENRE_CACHE_TTL_SECONDS = 24 * 60 * 60

def get_http_client(request: Request) -> httpx.AsyncClient:
    if hasattr(request.app.state, "http_client") and request.app.state.http_client is not None:
        return request.app.state.http_client
    return httpx.AsyncClient()


class MovieItem(BaseModel):
    id: str
    title: str
    poster_path: Optional[str] = None
    vote_average: float
    genres: List[str]
    match_score: float


class RecommendationResponse(BaseModel):
    algorithm: str
    movies: List[MovieItem]


SVD_MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "ml",
    "models",
    "svd_v1.pkl",
)

_svd_model = None
_tmdb_genre_map: Dict[int, str] = {}


def _tmdb_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.tmdb_api_key}",
        "accept": "application/json",
    }


def _get_svd_model():
    global _svd_model

    if _svd_model is not None:
        return _svd_model

    if os.path.exists(SVD_MODEL_PATH):
        try:
            with open(SVD_MODEL_PATH, "rb") as file:
                _svd_model = pickle.load(file)
            return _svd_model
        except Exception as error:
            logger.error(
                "failed_to_load_svd_model",
                error=str(error),
            )

    return None


def _hash_user_id_to_ml_id(user_id: str) -> str:
    """Map a string user ID to a stable MovieLens user ID."""
    hashed = int(
        hashlib.md5(user_id.encode()).hexdigest(),
        16,
    )
    return str((hashed % 943) + 1)


def _calculate_match_score(
    vote_average: float,
    popularity: float,
) -> float:
    normalized_vote = min(
        max(float(vote_average or 0.0) / 10.0, 0.0),
        1.0,
    )
    safe_popularity = max(float(popularity or 0.0), 0.0)
    normalized_popularity = (
        safe_popularity / (safe_popularity + 1000.0)
        if safe_popularity
        else 0.0
    )

    return round(
        (normalized_vote * 0.8)
        + (normalized_popularity * 0.2),
        2,
    )


def _resolve_genres(genre_ids: List[int]) -> List[str]:
    genres = [
        _tmdb_genre_map[genre_id]
        for genre_id in genre_ids
        if genre_id in _tmdb_genre_map
    ]
    return genres or ["Unknown"]





async def initialize_tmdb_genres(client: Optional[httpx.AsyncClient] = None) -> Dict[int, str]:
    """Load TMDB genres once. If a shared client is provided use it; otherwise fall back to a temporary client."""
    global _tmdb_genre_map

    if _tmdb_genre_map:
        return _tmdb_genre_map

    if not settings.tmdb_api_key:
        logger.warning(
            "tmdb_genres_not_loaded",
            reason="TMDB API key is not configured",
        )
        return {}

    redis = get_redis()

    if redis:
        try:
            cached_data = redis.get(TMDB_GENRE_CACHE_KEY)
            if cached_data:
                raw_mapping = json.loads(cached_data)
                _tmdb_genre_map = {
                    int(genre_id): name
                    for genre_id, name in raw_mapping.items()
                }
                logger.info(
                    "tmdb_genre_cache_hit",
                    genres=len(_tmdb_genre_map),
                )
                return _tmdb_genre_map
        except Exception as error:
            logger.error(
                "tmdb_genre_cache_read_failed",
                error=str(error),
            )

    try:
        if client is None:
            async with httpx.AsyncClient() as temp_client:
                response = await temp_client.get(
                    f"{TMDB_BASE_URL}/genre/movie/list",
                    params={"language": "en-US"},
                    headers=_tmdb_headers(),
                )
                response.raise_for_status()
        else:
            response = await client.get(
                f"{TMDB_BASE_URL}/genre/movie/list",
                params={"language": "en-US"},
                headers=_tmdb_headers(),
            )
            response.raise_for_status()

        _tmdb_genre_map = {
            int(genre["id"]): str(genre["name"])
            for genre in response.json().get("genres", [])
            if genre.get("id") is not None and genre.get("name")
        }

        if redis and _tmdb_genre_map:
            try:
                redis.setex(
                    TMDB_GENRE_CACHE_KEY,
                    TMDB_GENRE_CACHE_TTL_SECONDS,
                    json.dumps(_tmdb_genre_map),
                )
            except Exception as error:
                logger.error(
                    "tmdb_genre_cache_write_failed",
                    error=str(error),
                )

        logger.info(
            "tmdb_genres_loaded",
            genres=len(_tmdb_genre_map),
        )
    except Exception as error:
        logger.error(
            "tmdb_genre_fetch_failed",
            error=str(error),
        )

    return _tmdb_genre_map


async def _fetch_tmdb_movies(
    endpoint: str,
    limit: int = 20,
    page: int = 1,
    client: Optional[httpx.AsyncClient] = None,
) -> List[MovieItem]:
    if not settings.tmdb_api_key:
        return []

    if not _tmdb_genre_map:
        await initialize_tmdb_genres(client)

    redis = get_redis()
    cache_key = None

    if endpoint == "movie/popular":
        cache_key = f"tmdb:popular:page:{page}"
    elif endpoint == "trending/movie/day":
        cache_key = f"tmdb:trending:page:{page}"

    if redis and cache_key:
        try:
            cached_data = redis.get(cache_key)
            if cached_data:
                logger.info(
                    "tmdb_cache_hit",
                    key=cache_key,
                )
                items = json.loads(cached_data)
                return [
                    MovieItem(**item)
                    for item in items
                ][:limit]
        except Exception as error:
            logger.error(
                "redis_cache_error",
                error=str(error),
            )

    try:
        if client is None:
            async with httpx.AsyncClient() as temp_client:
                response = await temp_client.get(
                    f"{TMDB_BASE_URL}/{endpoint}",
                    params={
                        "language": "en-US",
                        "page": page,
                    },
                    headers=_tmdb_headers(),
                )
                response.raise_for_status()
        else:
            response = await client.get(
                f"{TMDB_BASE_URL}/{endpoint}",
                params={
                    "language": "en-US",
                    "page": page,
                },
                headers=_tmdb_headers(),
            )
            response.raise_for_status()

        movies = [
            MovieItem(
                id=str(item.get("id")),
                title=item.get("title", ""),
                poster_path=(
                    f"{TMDB_IMAGE_BASE_URL}{item.get('poster_path')}"
                    if item.get("poster_path")
                    else None
                ),
                vote_average=float(
                    item.get("vote_average", 0.0) or 0.0,
                ),
                genres=_resolve_genres(
                    item.get("genre_ids", []),
                ),
                match_score=_calculate_match_score(
                    item.get("vote_average", 0.0),
                    item.get("popularity", 0.0),
                ),
            )
            for item in response.json().get("results", [])[:limit]
        ]

        if redis and cache_key:
            try:
                redis.setex(
                    cache_key,
                    3600,
                    json.dumps(
                        [
                            movie.model_dump()
                            for movie in movies
                        ],
                    ),
                )
            except Exception as error:
                logger.error(
                    "redis_cache_set_error",
                    error=str(error),
                )

        return movies
    except Exception as error:
        logger.error(
            "tmdb_fetch_failed",
            endpoint=endpoint,
            error=str(error),
        )
        return []


async def _fetch_tmdb_movie_by_id(
    movie_id: str,
    match_score: float,
    client: Optional[httpx.AsyncClient] = None,
) -> Optional[MovieItem]:
    if not settings.tmdb_api_key:
        return None

    try:
        if client is None:
            async with httpx.AsyncClient() as temp_client:
                response = await temp_client.get(
                    f"{TMDB_BASE_URL}/movie/{movie_id}",
                    params={"language": "en-US"},
                    headers=_tmdb_headers(),
                )
                response.raise_for_status()
        else:
            response = await client.get(
                f"{TMDB_BASE_URL}/movie/{movie_id}",
                params={"language": "en-US"},
                headers=_tmdb_headers(),
            )
            response.raise_for_status()

        item = response.json()
        genres = [
            genre.get("name")
            for genre in item.get("genres", [])
            if genre.get("name")
        ]

        return MovieItem(
            id=str(item.get("id")),
            title=item.get("title", ""),
            poster_path=(
                f"{TMDB_IMAGE_BASE_URL}{item.get('poster_path')}"
                if item.get("poster_path")
                else None
            ),
            vote_average=float(
                item.get("vote_average", 0.0) or 0.0,
            ),
            genres=genres or ["Unknown"],
            match_score=round(match_score, 2),
        )
    except Exception as error:
        logger.error(
            "tmdb_fetch_by_id_failed",
            movie_id=movie_id,
            error=str(error),
        )
        return None


@router.get(
    "/personalized",
    response_model=RecommendationResponse,
)
async def get_personalized_recommendations(
    user_id: str = Depends(get_current_user),
    limit: int = Query(20, le=100),
    page: int = Query(default=1, ge=1, le=1000, description="Page number"),
    db: AsyncSession = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_http_client),
    request: Request = None,
):
    """Get personalized recommendations using Redis cache first; fall back to popularity rank for cold-start."""
    logger.info("fetch_personalized_recs", user_id=user_id, limit=limit, page=page)

    redis = get_redis()
    if redis:
        try:
            key = f"rec:user:{user_id}"
            cached_data = redis.get(key)
            if cached_data:
                logger.info("personalized_recs_cache_hit", user_id=user_id)
                movies_list = json.loads(cached_data)
                offset = (page - 1) * limit
                paginated_movies = movies_list[offset : offset + limit]
                return RecommendationResponse(
                    algorithm="collaborative_filtering_redis",
                    movies=[MovieItem(**m) for m in paginated_movies]
                )
        except Exception as e:
            logger.error("personalized_recs_cache_fetch_failed", error=str(e))

    # Cold start fallback - fetch popularity rank from PostgreSQL
    try:
        offset = (page - 1) * limit
        stmt = select(Movie).order_by(Movie.popularity.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        db_movies = result.scalars().all()
        if db_movies:
            movies = []
            for item in db_movies:
                match_score = round(0.65 + (item.popularity / 2000.0) * 0.33, 2)
                match_score = min(match_score, 0.99)
                movies.append(
                    MovieItem(
                        id=item.id,
                        title=item.title,
                        poster_path=item.poster_path,
                        vote_average=item.vote_average,
                        genres=item.genres or ["Movie"],
                        match_score=match_score
                    )
                )
            return RecommendationResponse(algorithm="popularity_rank_fallback", movies=movies)
    except Exception as e:
        logger.warning("postgres_popularity_fallback_failed", error=str(e))

    # Ultimate fallback: fetch from TMDB popular
    movies = await _fetch_tmdb_movies("movie/popular", limit, page)
    if not movies:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendations are unavailable: configure TMDB_API_KEY and populate the movie catalogue."
        )

    return RecommendationResponse(algorithm="cold_start_fallback", movies=movies)


@router.get(
    "/trending",
    response_model=RecommendationResponse,
)
async def get_trending_movies(
    limit: int = Query(20, le=100),
    page: int = Query(default=1, ge=1, le=1000, description="Page number"),
    db: AsyncSession = Depends(get_db),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Get globally trending movies from PostgreSQL DB, TMDB, or Fallback."""
    logger.info("fetch_trending_movies", limit=limit, page=page)

    # 1. Try PostgreSQL DB first
    try:
        offset = (page - 1) * limit
        stmt = select(Movie).order_by(Movie.popularity.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        db_movies = result.scalars().all()
        if db_movies:
            movies = []
            for item in db_movies:
                match_score = round(0.65 + (item.popularity / 2000.0) * 0.33, 2)
                match_score = min(match_score, 0.99)
                movies.append(
                    MovieItem(
                        id=item.id,
                        title=item.title,
                        poster_path=item.poster_path,
                        vote_average=item.vote_average,
                        genres=item.genres or ["Movie"],
                        match_score=match_score
                    )
                )
            return RecommendationResponse(algorithm="postgres_popularity_rank", movies=movies)
    except Exception as e:
        logger.warning("postgres_trending_fallback", error=str(e))

    # 2. Try the configured TMDB API.
    movies = await _fetch_tmdb_movies("trending/movie/day", limit, page, client=client)
    if not movies:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Trending movies are unavailable: configure TMDB_API_KEY and populate the movie catalogue.")

    return RecommendationResponse(algorithm="trending_fallback", movies=movies)


@router.get(
    "/by-emotion",
    response_model=RecommendationResponse,
)
async def get_recommendations_by_emotion(
    emotion: str = Query(..., description="Emotion/mood to filter by e.g. Tense, Adrenaline, Mind-Bending, Feel-Good"),
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Get movie recommendations filtered by dominant_emotion sorted by popularity.
    """
    logger.info("fetch_recs_by_emotion", emotion=emotion, limit=limit)
    clean_emotion = emotion.strip()

    try:
        stmt = (
            select(Movie)
            .where(Movie.dominant_emotion.ilike(f"%{clean_emotion}%"))
            .order_by(Movie.popularity.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        db_movies = result.scalars().all()

        if not db_movies:
            stmt = select(Movie).order_by(Movie.popularity.desc()).limit(limit)
            result = await db.execute(stmt)
            db_movies = result.scalars().all()

        movies = [
            MovieItem(
                id=item.id,
                title=item.title,
                poster_path=item.poster_path,
                vote_average=item.vote_average,
                genres=item.genres or ["Movie"],
                match_score=min(round(0.70 + (item.popularity / 2000.0) * 0.28, 2), 0.99),
            )
            for item in db_movies
        ]
        return RecommendationResponse(
            algorithm=f"emotion_filter_{clean_emotion.lower()}",
            movies=movies,
        )
    except Exception as e:
        logger.warning("by_emotion_query_failed", error=str(e))
        return RecommendationResponse(algorithm="emotion_fallback", movies=[])

