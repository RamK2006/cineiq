from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
import structlog
import httpx
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.db.models import Movie

logger = structlog.get_logger()
router = APIRouter(prefix="/movie", tags=["movie"])

class EmotionalArcPoint(BaseModel):
    time: str
    tension: float
    awe: float
    action: float

class MovieDetailResponse(BaseModel):
    id: str
    title: str
    tagline: Optional[str] = None
    overview: str
    year: str
    runtime: Optional[str] = None
    rating: Optional[str] = None
    genres: List[str]
    director: Optional[str] = None
    cast: List[str]
    backdrop: Optional[str] = None
    dominant_emotion: Optional[str] = None
    match: float
    emotional_arc: List[EmotionalArcPoint]

async def _fetch_tmdb_extra_details(movie_id: str):
    """Fetch additional details (cast, director, runtime, tagline) from TMDB."""
    details = {"tagline": None, "runtime": None, "rating": None, "director": None, "cast": []}
    
    if not settings.tmdb_api_key or "placeholder" in settings.tmdb_api_key.lower():
        return details
        
    try:
        async with httpx.AsyncClient() as client:
            # 1. Fetch main details
            resp = await client.get(
                f"https://api.themoviedb.org/3/movie/{movie_id}",
                params={"language": "en-US"},
                headers={
                    "Authorization": f"Bearer {settings.tmdb_api_key}",
                    "accept": "application/json"
                },
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                runtime_mins = data.get("runtime", 0)
                hours = runtime_mins // 60
                mins = runtime_mins % 60
                details["runtime"] = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
                details["tagline"] = data.get("tagline", "")
                
            # 2. Fetch credits
            resp_credits = await client.get(
                f"https://api.themoviedb.org/3/movie/{movie_id}/credits",
                headers={
                    "Authorization": f"Bearer {settings.tmdb_api_key}",
                    "accept": "application/json"
                },
                timeout=5.0
            )
            if resp_credits.status_code == 200:
                credits_data = resp_credits.json()
                cast_list = [member.get("name") for member in credits_data.get("cast", [])[:4]]
                if cast_list:
                    details["cast"] = cast_list
                    
                crew = credits_data.get("crew", [])
                for member in crew:
                    if member.get("job") == "Director":
                        details["director"] = member.get("name")
                        break
    except Exception as e:
        logger.error("tmdb_extra_details_failed", movie_id=movie_id, error=str(e))
        
    return details

@router.get("/{movie_id}", response_model=MovieDetailResponse)
async def get_movie_details(
    movie_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve detailed movie metadata, combining PostgreSQL and dynamic TMDB queries."""
    logger.info("get_movie_details", movie_id=movie_id)
    
    # 1. Get main info from local DB
    stmt = select(Movie).where(Movie.id == movie_id)
    result = await db.execute(stmt)
    movie = result.scalars().first()
    
    # 2. If movie not in local DB, fetch basic info from TMDB and cache it
    if not movie:
        if settings.tmdb_api_key and "placeholder" not in settings.tmdb_api_key.lower():
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"https://api.themoviedb.org/3/movie/{movie_id}",
                        headers={
                            "Authorization": f"Bearer {settings.tmdb_api_key}",
                            "accept": "application/json"
                        },
                        timeout=5.0
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        release_date_str = data.get("release_date")
                        from datetime import datetime
                        release_date = None
                        if release_date_str:
                            try:
                                release_date = datetime.strptime(release_date_str, "%Y-%m-%d")
                            except ValueError:
                                pass
                        
                        movie = Movie(
                            id=movie_id,
                            title=data.get("title") or "Untitled",
                            overview=data.get("overview", ""),
                            release_date=release_date,
                            poster_path=f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get("poster_path") else None,
                            backdrop_path=f"https://image.tmdb.org/t/p/original{data.get('backdrop_path')}" if data.get("backdrop_path") else None,
                            genres=[g.get("name") for g in data.get("genres", []) if g.get("name")],
                            popularity=float(data.get("popularity", 0.0)),
                            vote_average=float(data.get("vote_average", 0.0)),
                            vote_count=int(data.get("vote_count", 0)),
                            dominant_emotion=None,
                            emotional_arc=None,
                        )
                        db.add(movie)
                        await db.commit()
                        logger.info("cached_movie_from_tmdb", movie_id=movie_id)
            except Exception as e:
                logger.error("fetch_tmdb_movie_failed", movie_id=movie_id, error=str(e))
                
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
        
    # 3. Fetch extra dynamic info (tagline, cast, director, runtime) from TMDB
    extra = await _fetch_tmdb_extra_details(movie_id)
    
    # 4. format release year
    year = str(movie.release_date.year) if movie.release_date else "Unknown"
    
    # 5. Calculate match score
    match_score = round(0.70 + (movie.vote_average / 10.0) * 0.28, 2) * 100
    
    # 6. Format emotional arc
    emotional_arc_list = []
    if movie.emotional_arc:
        for pt in movie.emotional_arc:
            emotional_arc_list.append(
                EmotionalArcPoint(
                    time=pt.get("time", "0m"),
                    tension=pt.get("tension", 0.0),
                    awe=pt.get("awe", 0.0),
                    action=pt.get("action", 0.0)
                )
            )
            
    return MovieDetailResponse(
        id=movie.id,
        title=movie.title,
        tagline=extra["tagline"],
        overview=movie.overview,
        year=year,
        runtime=extra["runtime"],
        rating=extra["rating"],
        genres=movie.genres or [],
        director=extra["director"],
        cast=extra["cast"],
        backdrop=movie.backdrop_path,
        dominant_emotion=movie.dominant_emotion,
        match=match_score,
        emotional_arc=emotional_arc_list
    )


class SimilarMovieItem(BaseModel):
    id: str
    title: str
    poster_path: Optional[str] = None
    vote_average: float
    genres: List[str]
    match_score: float


class SimilarMoviesResponse(BaseModel):
    movie_id: str
    algorithm: str
    movies: List[SimilarMovieItem]


def _calculate_jaccard_similarity(genres1: List[str], genres2: List[str]) -> float:
    set1 = set(g.lower() for g in (genres1 or []))
    set2 = set(g.lower() for g in (genres2 or []))
    if not set1 or not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return float(intersection / union) if union > 0 else 0.0


@router.get("/{movie_id}/similar", response_model=SimilarMoviesResponse)
async def get_similar_movies(
    movie_id: str,
    limit: int = 8,
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate hybrid genre Jaccard similarity + popularity & vote weight to recommend similar movies ("More Like This").
    Excludes the target movie_id.
    """
    logger.info("get_similar_movies", movie_id=movie_id, limit=limit)
    
    # 1. Fetch target movie
    stmt = select(Movie).where(Movie.id == movie_id)
    result = await db.execute(stmt)
    target_movie = result.scalars().first()
    
    if not target_movie:
        raise HTTPException(status_code=404, detail="Movie not found")
        
    target_genres = target_movie.genres or []
    
    # 2. Fetch candidate movies excluding target movie
    cand_stmt = select(Movie).where(Movie.id != movie_id).order_by(Movie.popularity.desc()).limit(100)
    cand_res = await db.execute(cand_stmt)
    candidates = cand_res.scalars().all()
    
    scored_movies = []
    for cand in candidates:
        jaccard = _calculate_jaccard_similarity(target_genres, cand.genres or [])
        pop_weight = cand.popularity / (cand.popularity + 1000.0) if cand.popularity else 0.0
        vote_weight = (cand.vote_average or 0.0) / 10.0
        
        hybrid_score = (0.60 * jaccard) + (0.20 * pop_weight) + (0.20 * vote_weight)
        match_score = round(min(hybrid_score, 0.99), 2)
        
        scored_movies.append((hybrid_score, cand, match_score))
        
    scored_movies.sort(key=lambda x: x[0], reverse=True)
    
    similar_items = [
        SimilarMovieItem(
            id=cand.id,
            title=cand.title,
            poster_path=cand.poster_path,
            vote_average=cand.vote_average or 0.0,
            genres=cand.genres or [],
            match_score=match_score,
        )
        for _, cand, match_score in scored_movies[:limit]
    ]
    
    return SimilarMoviesResponse(
        movie_id=movie_id,
        algorithm="hybrid_jaccard_similarity",
        movies=similar_items
    )

