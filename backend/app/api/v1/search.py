from fastapi import APIRouter, Query
from typing import List, Optional
from pydantic import BaseModel
import structlog
import httpx

from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/search", tags=["search"])

class SearchResult(BaseModel):
    id: str
    title: str
    overview: str
    poster_path: Optional[str] = None
    similarity_score: float

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]

@router.get("/semantic", response_model=SearchResponse)
async def semantic_search(
    q: str = Query(..., description="Natural language search query"),
    limit: int = Query(10, le=50)
):
    """
    Perform semantic search using Google Gemini for intent extraction and TMDB API.
    Example: 'a dark sci-fi movie about time travel'
    """
    logger.info("semantic_search", query=q, limit=limit)
    
    keywords = q
    
    if settings.gemini_api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel(settings.gemini_model)
            
            prompt = f"""Extract main keywords from this movie search query to be used in a search engine. 
            Return ONLY the keywords separated by spaces.
            Query: "{q}"
            """
            
            response = model.generate_content(prompt)
            if response.text:
                 keywords = response.text.strip()
        except Exception as e:
            logger.warning("gemini_keyword_extraction_failed", error=str(e))
            
    # Fallback to TMDB Search
    results = []
    if settings.tmdb_api_key:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.themoviedb.org/3/search/movie",
                    params={
                        "query": keywords,
                        "include_adult": "false",
                        "language": "en-US",
                        "page": 1
                    },
                    headers={
                        "Authorization": f"Bearer {settings.tmdb_api_key}",
                        "accept": "application/json"
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("results", [])[:limit]:
                        results.append(
                            SearchResult(
                                id=str(item.get("id")),
                                title=item.get("title", ""),
                                overview=item.get("overview", ""),
                                poster_path=f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get("poster_path") else None,
                                similarity_score=0.9 # Mocked similarity
                            )
                        )
        except Exception as e:
            logger.error("tmdb_search_failed", error=str(e))
    else:
        # Placeholder for actual embedding + Qdrant search if no TMDB api key
        results = [
            SearchResult(
                id="12",
                title="Arrival",
                overview="A linguist works with the military to communicate with alien lifeforms.",
                similarity_score=0.89
            )
        ]
    
    return SearchResponse(query=q, results=results)
