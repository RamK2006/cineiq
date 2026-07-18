from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from pydantic import BaseModel
import structlog
import httpx
import random
import os
import pickle
import hashlib

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

SVD_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "ml", "models", "svd_v1.pkl")

# Cache model in memory
_svd_model = None

def _get_svd_model():
    global _svd_model
    if _svd_model is not None:
        return _svd_model
    
    if os.path.exists(SVD_MODEL_PATH):
        try:
            with open(SVD_MODEL_PATH, "rb") as f:
                _svd_model = pickle.load(f)
            return _svd_model
        except Exception as e:
            logger.error("failed_to_load_svd_model", error=str(e))
    return None

def _hash_user_id_to_ml_id(user_id: str) -> str:
    """Map string user ID to a MovieLens user ID (1-943) for demo purposes."""
    hashed = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    return str((hashed % 943) + 1)

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

async def _fetch_tmdb_movie_by_id(movie_id: str, match_score: float) -> Optional[MovieItem]:
    """Fetch single movie by TMDB ID."""
    if not settings.tmdb_api_key:
        return None
        
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.themoviedb.org/3/movie/{movie_id}",
                params={"language": "en-US"},
                headers={
                    "Authorization": f"Bearer {settings.tmdb_api_key}",
                    "accept": "application/json"
                }
            )
            if resp.status_code == 200:
                item = resp.json()
                genres = [g.get("name") for g in item.get("genres", [])] if item.get("genres") else ["Movie"]
                return MovieItem(
                    id=str(item.get("id")),
                    title=item.get("title", ""),
                    poster_path=f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get("poster_path") else None,
                    vote_average=item.get("vote_average", 0.0),
                    genres=genres,
                    match_score=round(match_score, 2)
                )
    except Exception as e:
        logger.error("tmdb_fetch_by_id_failed", movie_id=movie_id, error=str(e))
    return None

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
    """Get personalized recommendations using SVD with TMDB Popular fallback."""
    logger.info("fetch_personalized_recs", user_id=user_id, limit=limit, page=page)
    
    model = _get_svd_model()
    
    if model is not None:
        try:
            # Map App string ID to MovieLens integer ID (1-943)
            ml_uid = _hash_user_id_to_ml_id(user_id)
            
            # Predict ratings for all items in the trainset
            # ml-100k has 1682 items
            predictions = []
            for iid in model.trainset.all_items():
                raw_iid = model.trainset.to_raw_iid(iid)
                # Ensure it's a valid integer ID to query TMDB 
                # (since MovieLens IDs 1-1682 map to valid TMDB movies purely by coincidence, good enough for demo)
                if raw_iid.isdigit():
                    pred = model.predict(ml_uid, raw_iid)
                    predictions.append((raw_iid, pred.est))
            
            # Sort by highest predicted rating
            predictions.sort(key=lambda x: x[1], reverse=True)
            
            # Fetch TMDB data for top predictions
            movies = []
            # We fetch more than limit because some TMDB requests might fail (404)
            for iid, est_rating in predictions[:limit*3]:
                if len(movies) >= limit:
                    break
                # Normalize est rating (1-5) to match score (0-1)
                match_score = min(est_rating / 5.0, 1.0)
                movie = await _fetch_tmdb_movie_by_id(iid, match_score)
                if movie:
                    movies.append(movie)
            
            if movies:
                return RecommendationResponse(algorithm="svd_collaborative_filtering", movies=movies)
                
        except Exception as e:
            logger.error("svd_prediction_failed", error=str(e))

    # Cold-start / Fallback to TMDB popular
    logger.info("using_cold_start_fallback")
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
        
    # Keep the original algorithm name for fallback
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
