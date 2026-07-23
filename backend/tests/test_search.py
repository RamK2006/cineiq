from unittest import mock
import httpx
from app.core.config import settings

def test_search_valid_request(client, monkeypatch):
    """Test standard semantic search with both Gemini and TMDB configured."""
    monkeypatch.setattr(settings, "gemini_api_key", "test_gemini_key")
    monkeypatch.setattr(settings, "tmdb_api_key", "test_tmdb_key")
    
    response = client.get("/api/v1/search/semantic?q=fight+club")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "fight club"
    assert len(data["results"]) > 0
    assert data["results"][0]["title"] == "Inception" # Mocked TMDB search result

def test_search_missing_query(client):
    """Test that missing the search query 'q' returns 422 validation error."""
    response = client.get("/api/v1/search/semantic")
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert data["error_code"] == "VALIDATION_ERROR"

def test_search_gemini_success_passes_to_tmdb(client, monkeypatch):
    """Test that Gemini keyword extraction is used for TMDB search."""
    monkeypatch.setattr(settings, "gemini_api_key", "test_gemini_key")
    monkeypatch.setattr(settings, "tmdb_api_key", "test_tmdb_key")
    
    # We will spy on the httpx client call to ensure it requests with Gemini's extracted keywords
    spy_called_with = None
    
    original_get = httpx.AsyncClient.get
    async def mock_spy_get(self, url, *args, **kwargs):
        nonlocal spy_called_with
        if "search/movie" in url:
            spy_called_with = kwargs.get("params", {}).get("query")
        return await original_get(self, url, *args, **kwargs)
        
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_spy_get)
    
    response = client.get("/api/v1/search/semantic?q=dark+sci+fi+thriller")
    assert response.status_code == 200
    assert spy_called_with == "inception dark sci-fi" # This comes from our conftest.py gemini mock

def test_search_gemini_failure_fallback(client, monkeypatch):
    """Test that if Gemini fails/raises error, it falls back to using original query for TMDB."""
    monkeypatch.setattr(settings, "gemini_api_key", "test_gemini_key")
    monkeypatch.setattr(settings, "tmdb_api_key", "test_tmdb_key")
    
    spy_called_with = None
    original_get = httpx.AsyncClient.get
    async def mock_spy_get(self, url, *args, **kwargs):
        nonlocal spy_called_with
        if "search/movie" in url:
            spy_called_with = kwargs.get("params", {}).get("query")
        return await original_get(self, url, *args, **kwargs)
        
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_spy_get)
    
    with mock.patch("google.generativeai.GenerativeModel", side_effect=Exception("Gemini API Quota Exceeded")):
        response = client.get("/api/v1/search/semantic?q=dark+sci+fi+thriller")
        assert response.status_code == 200
        assert spy_called_with == "dark sci fi thriller" # Falls back to the query


def test_search_tmdb_missing_key_fallback(client, monkeypatch):
    """Test that if TMDB key is missing, semantic search returns the static placeholder (Arrival)."""
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "tmdb_api_key", "")
    
    response = client.get("/api/v1/search/semantic?q=dark+sci+fi")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["title"] == "Arrival"
    assert data["results"][0]["similarity_score"] == 0.89

def test_search_tmdb_failure_fallback(client, monkeypatch):
    """Test that if TMDB API request fails, search catches exception and returns empty list."""
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "tmdb_api_key", "test_tmdb_key")
    
    async def mock_get_fail(*args, **kwargs):
        raise httpx.ConnectError("TMDB connection timed out")
        
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get_fail)
    
    response = client.get("/api/v1/search/semantic?q=dark+sci+fi")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 0
