import asyncio
import os
import structlog
from typing import List, Dict, Any
from sqlalchemy.future import select

from app.db.session import AsyncSessionLocal
from app.db.models import Movie
from app.services.embeddings import get_embedder

logger = structlog.get_logger(__name__)

# Qdrant client is optional, if not installed we mock it for fallback
try:
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("qdrant_client_not_installed", msg="pip install qdrant-client to enable vector search")

COLLECTION_NAME = "movies"
VECTOR_SIZE = 768  # Assuming Gemini default text-embedding-004 size. all-MiniLM-L6-v2 is 384.

class QdrantIndexer:
    def __init__(self, qdrant_url: str = "http://localhost:6333", vector_size: int = VECTOR_SIZE):
        self.qdrant_url = qdrant_url
        self.vector_size = vector_size
        self.client = AsyncQdrantClient(url=self.qdrant_url) if QDRANT_AVAILABLE else None
        self.embedder = get_embedder()
        
    async def ensure_collection(self):
        if not self.client:
            return
            
        collections = await self.client.get_collections()
        exists = any(c.name == COLLECTION_NAME for c in collections.collections)
        
        if not exists:
            logger.info("creating_qdrant_collection", collection=COLLECTION_NAME, size=self.vector_size)
            await self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )
        else:
            logger.info("qdrant_collection_exists", collection=COLLECTION_NAME)

    async def get_all_movies(self) -> List[Movie]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Movie))
            return result.scalars().all()

    def construct_movie_text(self, movie: Movie) -> str:
        """Constructs a dense semantic document representing the movie."""
        genres_str = ", ".join([str(g) for g in (movie.genres or [])])
        return f"Title: {movie.title}. Genres: {genres_str}. Overview: {movie.overview}"

    async def index_movies(self, batch_size: int = 50):
        if not self.client:
            logger.error("indexing_aborted", reason="Qdrant Client not available")
            return
            
        await self.ensure_collection()
        movies = await self.get_all_movies()
        logger.info("found_movies_for_indexing", count=len(movies))
        
        for i in range(0, len(movies), batch_size):
            batch = movies[i:i + batch_size]
            texts = [self.construct_movie_text(m) for m in batch]
            
            # Embed batch
            vectors = self.embedder.embed_batch(texts)
            
            # We must only push successful embeddings
            points = []
            for m, vector in zip(batch, vectors):
                if not vector:
                    continue
                    
                # Ensure Qdrant expects this size
                if len(vector) != self.vector_size:
                    logger.warning("vector_size_mismatch", expected=self.vector_size, got=len(vector))
                    continue
                    
                # Create point
                payload = {
                    "id": m.id,
                    "title": m.title,
                    "overview": m.overview,
                    "genres": m.genres
                }
                
                # Qdrant requires integer or UUID ids. If TMDB ID is string, we might need a hash.
                # Assuming m.id is convertible to UUID or Int
                import uuid
                point_id = str(uuid.uuid5(uuid.NAMESPACE_OID, str(m.id)))
                payload["original_movie_id"] = str(m.id)
                
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                )
                
            if points:
                await self.client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=points
                )
                logger.info("indexed_batch", start=i, end=i+len(batch), success_points=len(points))

async def run_indexer():
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    indexer = QdrantIndexer(qdrant_url=qdrant_url)
    
    # Auto-detect vector size based on embedder
    test_emb = indexer.embedder.embed_text("Test vector size")
    if test_emb:
        indexer.vector_size = len(test_emb)
        logger.info("auto_detected_vector_size", size=indexer.vector_size)
        
    await indexer.index_movies()

if __name__ == "__main__":
    asyncio.run(run_indexer())
