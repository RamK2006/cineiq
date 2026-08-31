
## 🔍 Qdrant Vector Search Setup

This project uses **Qdrant** to power dense vector semantic search over the movie catalog.

### Installation
1. Start Qdrant via Docker:
   ```bash
   docker run -p 6333:6333 -p 6334:6334 \
       -v $(pwd)/qdrant_storage:/qdrant/storage:z \
       qdrant/qdrant
   ```
2. Set the `QDRANT_URL` in your `.env`:
   ```env
   QDRANT_URL=http://localhost:6333
   ```

### Batch Indexing
To compute embeddings for the entire catalog and upsert them into Qdrant, run:
```bash
python -m app.services.index_qdrant
```

### Vector Index Stats
*   **Model**: Google Gemini `text-embedding-004` (Fallback: `all-MiniLM-L6-v2`)
*   **Dimensions**: 768 (Gemini) / 384 (SentenceTransformer)
*   **Distance Metric**: Cosine Similarity
*   **Document Structure**: `Title: {title}. Genres: {genres}. Overview: {overview}`

When `QDRANT_URL` is set, the `/api/v1/search/semantic` endpoint automatically upgrades from SQLite `LIKE` matching to True Semantic Vector Search.
