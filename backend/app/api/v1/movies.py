from typing import List, Optional

import httpx
import structlog
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/movies", tags=["movies"])


class CastMember(BaseModel):
    id: int
    name: str
    character: Optional[str] = None


class MovieDetail(BaseModel):
    id: str
    title: str
    tagline: str = ""
    overview: str = ""
    release_date: Optional[str] = None
    runtime: Optional[int] = None
    certification: Optional[str] = None
    genres: List[str] = []
    director: Optional[str] = None
    cast: List[CastMember] = []
    backdrop_path: Optional[str] = None
    poster_path: Optional[str] = None
    vote_average: float = 0.0
    match_score: float = 0.0


def _image_url(path: Optional[str], size: str) -> Optional[str]:
    if not path:
        return None
    return f"https://image.tmdb.org/t/p/{size}{path}"


def _certification(release_dates: dict) -> Optional[str]:
    for country in release_dates.get("results", []):
        if country.get("iso_3166_1") != "US":
            continue
        for item in country.get("release_dates", []):
            value = item.get("certification")
            if value:
                return value
    return None


@router.get("/{movie_id}", response_model=MovieDetail)
async def get_movie_detail(
    movie_id: int = Path(..., ge=1, description="TMDB movie ID"),
):
    if not settings.tmdb_api_key:
        raise HTTPException(status_code=503, detail="TMDB API is not configured")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"https://api.themoviedb.org/3/movie/{movie_id}",
                params={
                    "language": "en-US",
                    "append_to_response": "credits,release_dates",
                },
                headers={
                    "Authorization": f"Bearer {settings.tmdb_api_key}",
                    "accept": "application/json",
                },
            )
    except httpx.HTTPError as exc:
        logger.error("tmdb_movie_detail_failed", movie_id=movie_id, error=str(exc))
        raise HTTPException(status_code=502, detail="Unable to reach TMDB") from exc

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Movie not found")

    if response.status_code != 200:
        logger.error(
            "tmdb_movie_detail_error",
            movie_id=movie_id,
            status_code=response.status_code,
        )
        raise HTTPException(status_code=502, detail="Unable to load movie details")

    item = response.json()
    credits = item.get("credits", {})
    crew = credits.get("crew", [])
    director = next(
        (member.get("name") for member in crew if member.get("job") == "Director"),
        None,
    )

    cast = [
        CastMember(
            id=member.get("id", 0),
            name=member.get("name", "Unknown"),
            character=member.get("character"),
        )
        for member in credits.get("cast", [])[:8]
    ]

    vote_average = float(item.get("vote_average") or 0.0)

    return MovieDetail(
        id=str(item.get("id", movie_id)),
        title=item.get("title") or "Untitled",
        tagline=item.get("tagline") or "",
        overview=item.get("overview") or "",
        release_date=item.get("release_date"),
        runtime=item.get("runtime"),
        certification=_certification(item.get("release_dates", {})),
        genres=[genre.get("name") for genre in item.get("genres", []) if genre.get("name")],
        director=director,
        cast=cast,
        backdrop_path=_image_url(item.get("backdrop_path"), "original"),
        poster_path=_image_url(item.get("poster_path"), "w500"),
        vote_average=vote_average,
        match_score=round(min(max(vote_average / 10, 0.0), 1.0), 2),
    )
