from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from pydantic import BaseModel
import structlog
import httpx
import random

from app.core.security import get_current_user
from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/recommend", tags=["recommendation"])

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

async def _fetch_tmdb_movies(endpoint: str, limit: int = 20, page: int = 1) -> List[MovieItem]:
    if not settings.tmdb_api_key:
        return []
        
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.themoviedb.org/3/{endpoint}",
                params={"language": "en-US", "page": page},
                headers={
                    "Authorization": f"Bearer {settings.tmdb_api_key}",
                    "accept": "application/json"
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                movies = []
                for item in data.get("results", [])[:limit]:
                    movies.append(
                        MovieItem(
                            id=str(item.get("id")),
                            title=item.get("title", ""),
                            poster_path=f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get("poster_path") else None,
                            vote_average=item.get("vote_average", 0.0),
                            genres=["Movie"], # Would need genre mapping
                            match_score=round(random.uniform(0.7, 0.98), 2)
                        )
                    )
                return movies
    except Exception as e:
        logger.error("tmdb_fetch_failed", endpoint=endpoint, error=str(e))
    return []

@router.get("/personalized", response_model=RecommendationResponse)
async def get_personalized_recommendations(
    user_id: str = Depends(get_current_user),
    limit: int = Query(20, le=100),
    page: int = Query(
        default=1,
        ge=1,
        le=1000,
        description="TMDB page number"
    )
):
    """Get personalized recommendations (TMDB Popular fallback for serverless demo)."""
    logger.info("fetch_personalized_recs", user_id=user_id, limit=limit, page=page)
    
    movies = await _fetch_tmdb_movies("movie/popular", limit, page)
    
    if not movies:
        # Return mock data if TMDB fails or key not set
        movies = [
            MovieItem(
                id="1", 
                title="Inception", 
                vote_average=8.8, 
                genres=["Action", "Sci-Fi"],
                match_score=0.95
            ),
            MovieItem(
                id="2", 
                title="Interstellar", 
                vote_average=8.6, 
                genres=["Adventure", "Sci-Fi"],
                match_score=0.92
            )
        ]
        
    return RecommendationResponse(algorithm="hybrid_ncf_svd_mock", movies=movies)

@router.get("/trending", response_model=RecommendationResponse)
async def get_trending_movies(
    limit: int = Query(20, le=100),
    page: int = Query(
        default=1,
        ge=1,
        le=1000,
        description="TMDB page number"
    )
):
    """Get globally trending movies."""
    movies = await _fetch_tmdb_movies("trending/movie/day", limit, page)
    
    if not movies:
        movies = [
            MovieItem(
                id="3", 
                title="Dune: Part Two", 
                vote_average=8.3, 
                genres=["Sci-Fi", "Adventure"],
                match_score=0.88
            )
        ]
        
    return RecommendationResponse(algorithm="trending", movies=movies)
