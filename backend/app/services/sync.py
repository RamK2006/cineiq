"""Synchronise the local catalogue with TMDB without inventing catalogue data."""

from datetime import datetime

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Movie

logger = structlog.get_logger()

GENRE_MAP = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
    80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
    14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
    9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 10770: "TV Movie",
    53: "Thriller", 10752: "War", 37: "Western",
}


async def seed_movies_if_empty(db: AsyncSession) -> None:
    """Import initial catalogue data from TMDB when the database is empty.

    Missing or failing external data is surfaced in logs; it is never replaced
    with a hardcoded catalogue.
    """
    if (await db.execute(select(Movie.id).limit(1))).scalar_one_or_none():
        return
    if not settings.tmdb_api_key or "placeholder" in settings.tmdb_api_key.lower():
        logger.warning("tmdb_not_configured_catalogue_not_seeded")
        return

    movies: dict[str, Movie] = {}
    async with httpx.AsyncClient(timeout=15.0) as client:
        for endpoint in ("movie/popular", "trending/movie/day"):
            try:
                response = await client.get(
                    f"https://api.themoviedb.org/3/{endpoint}",
                    params={"language": "en-US", "page": 1},
                    headers={"Authorization": f"Bearer {settings.tmdb_api_key}", "accept": "application/json"},
                )
                response.raise_for_status()
            except httpx.HTTPError as error:
                logger.error("tmdb_catalogue_sync_failed", endpoint=endpoint, error=str(error))
                continue

            for item in response.json().get("results", []):
                movie_id = str(item.get("id", ""))
                if not movie_id or movie_id in movies:
                    continue
                release_date = None
                if item.get("release_date"):
                    try:
                        release_date = datetime.strptime(item["release_date"], "%Y-%m-%d")
                    except ValueError:
                        pass
                movies[movie_id] = Movie(
                    id=movie_id,
                    title=item.get("title") or "Untitled",
                    overview=item.get("overview") or "",
                    release_date=release_date,
                    poster_path=(f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else None),
                    backdrop_path=(f"https://image.tmdb.org/t/p/original{item['backdrop_path']}" if item.get("backdrop_path") else None),
                    genres=[GENRE_MAP[genre_id] for genre_id in item.get("genre_ids", []) if genre_id in GENRE_MAP],
                    popularity=float(item.get("popularity") or 0),
                    vote_average=float(item.get("vote_average") or 0),
                    vote_count=int(item.get("vote_count") or 0),
                )
    if not movies:
        logger.warning("tmdb_catalogue_sync_returned_no_movies")
        return
    db.add_all(movies.values())
    await db.commit()
    logger.info("tmdb_catalogue_seeded", count=len(movies))
