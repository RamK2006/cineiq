import asyncio
import zipfile
import io
import csv
import re
import httpx
import structlog
from datetime import datetime
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import Movie

logger = structlog.get_logger()

async def import_10k_movies():
    """
    Downloads and parses the MovieLens 100k dataset (9,742 movies).
    This dataset requires no developer keys, registration, or accounts, making it fully accessible globally.
    """
    url = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
    logger.info("movielens_download_started", url=url)
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=45.0)
            if resp.status_code != 200:
                logger.error("movielens_download_failed", status=resp.status_code)
                return
    except Exception as e:
        logger.error("movielens_http_failed", error=str(e))
        return

    zip_bytes = io.BytesIO(resp.content)
    try:
        with zipfile.ZipFile(zip_bytes) as z:
            movies_file = None
            for name in z.namelist():
                if name.endswith("movies.csv"):
                    movies_file = name
                    break
                    
            if not movies_file:
                logger.error("movies_csv_not_found_in_zip")
                return
                
            logger.info("parsing_movies_csv", file=movies_file)
            with z.open(movies_file) as f:
                content = f.read().decode("utf-8")
                reader = csv.reader(io.StringIO(content))
                next(reader) # skip headers
                
                movies_list = []
                for row in reader:
                    if len(row) < 3:
                        continue
                    movie_id, title_raw, genres_raw = row[0], row[1], row[2]
                    
                    # Parse release year from title (e.g. "Toy Story (1995)" -> 1995)
                    title = title_raw.strip()
                    year = None
                    match = re.search(r"\((\d{4})\)$", title)
                    if match:
                        year = int(match.group(1))
                        title = re.sub(r"\s*\(\d{4}\)$", "", title)
                        
                    # Split and map genres
                    genres = [g.strip() for g in genres_raw.split("|") if g.strip()]
                    if genres == ["(no genres listed)"]:
                        genres = []
                        
                    release_date = datetime(year, 1, 1) if year else None
                    
                    movies_list.append({
                        "id": movie_id,
                        "title": title,
                        "overview": "",
                        "release_date": release_date,
                        "poster_path": None,
                        "backdrop_path": None,
                        "genres": genres,
                        "popularity": 0,
                        "vote_average": 0,
                        "vote_count": 0,
                    })
                    
                logger.info("csv_parsing_complete", count=len(movies_list))
                
                # 2. Write to database in batches using merge (portable: works on SQLite + PG)
                async with AsyncSessionLocal() as db:
                    total_inserted = 0
                    batch_size = 500
                    for i in range(0, len(movies_list), batch_size):
                        batch = movies_list[i:i+batch_size]
                        for movie_data in batch:
                            existing = await db.execute(
                                select(Movie).where(Movie.id == movie_data["id"])
                            )
                            if existing.scalars().first() is None:
                                db.add(Movie(**movie_data))
                        await db.commit()
                        total_inserted += len(batch)
                        logger.info("batch_inserted", progress=f"{total_inserted}/{len(movies_list)}")
                        
                logger.info("bulk_import_completed", total_inserted=total_inserted)
                
    except zipfile.BadZipFile:
        logger.error("invalid_zip_archive")
    except Exception as e:
        logger.error("bulk_import_failed", error=str(e))

if __name__ == "__main__":
    asyncio.run(import_10k_movies())
