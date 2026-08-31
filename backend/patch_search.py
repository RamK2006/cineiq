import re

with open('app/api/v1/search.py', 'r') as f:
    content = f.read()

replacement = """
    # 1. Try Qdrant vector search if enabled (skip if filters are applied)
    if settings.qdrant_url and not has_filters and q:
        try:
            from app.services.embeddings import get_embedder
            from qdrant_client import AsyncQdrantClient
            
            embedder = get_embedder()
            query_vector = embedder.embed_text(q)
            
            client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
            # AsyncQdrantClient collections API is async
            collections = await client.get_collections()
            
            if any(c.name == "movies" for c in collections.collections) and query_vector:
                qdrant_results = await client.search(
                    collection_name="movies",
                    query_vector=query_vector,
                    limit=limit
                )

                if qdrant_results:
                    logger.info("qdrant_search_success", query=q, hits=len(qdrant_results))
                    results = [
                        SearchResult(
                            id=str(hit.payload.get("original_movie_id", hit.id)),
                            title=hit.payload.get("title", "Unknown"),
                            overview=hit.payload.get("overview", ""),
                            poster_path=None, # Depending on payload structure
                            similarity_score=float(hit.score)
                        ) for hit in qdrant_results
                    ]
                    return SearchResponse(query=q, results=results)
        except Exception as e:
            logger.warning("qdrant_search_failed_falling_back", error=str(e))
"""

content = re.sub(
    r"# 1\. Try Qdrant vector search if enabled.*?logger\.warning\(\"qdrant_search_failed_falling_back\", error=str\(e\)\)",
    replacement.strip(),
    content,
    flags=re.DOTALL
)

with open('app/api/v1/search.py', 'w') as f:
    f.write(content)
