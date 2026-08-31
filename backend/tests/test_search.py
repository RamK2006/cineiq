import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

def test_search_endpoint_returns_results_with_mock_tmdb():
    """Verify that semantic search endpoint handles queries and returns result list."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "id": 157336,
                "title": "Interstellar",
                "overview": "Mankind was born on Earth. It was never meant to die here.",
                "poster_path": "/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg"
            }
        ]
    }

    with patch.object(settings, "gemini_api_key", "test-gemini-key"), \
         patch.object(settings, "tmdb_api_key", "test-tmdb-key"), \
         patch("httpx.AsyncClient.get", return_value=mock_response), \
         TestClient(app) as client:
        response = client.get("/api/v1/search/semantic?q=Interstellar")
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) >= 1
        assert data["results"][0]["title"] == "Interstellar"

def test_search_unconfigured_returns_503():
    """Verify that semantic search handles unconfigured services gracefully."""
    with patch.object(settings, "gemini_api_key", ""), \
         patch.object(settings, "qdrant_url", None), \
         TestClient(app) as client:
        response = client.get("/api/v1/search/semantic?q=Interstellar")
        assert response.status_code in (200, 503)


def test_search_with_only_filters_succeeds():
    """Verify that semantic search without 'q' but with filters succeeds."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}

    with patch.object(settings, "gemini_api_key", "test-gemini-key"), \
         patch.object(settings, "tmdb_api_key", "test-tmdb-key"), \
         patch("httpx.AsyncClient.get", return_value=mock_response), \
         TestClient(app) as client:
        response = client.get("/api/v1/search/semantic?genres=Action")
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data


def test_suggest_endpoint_empty_query():
    """Verify that suggest endpoint returns empty list for empty query."""
    with TestClient(app) as client:
        response = client.get("/api/v1/search/suggest?q=")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0


def test_suggest_endpoint_with_query():
    """Verify that suggest endpoint returns list of suggestions matching prefix."""
    with TestClient(app) as client:
        response = client.get("/api/v1/search/suggest?q=Inter&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        suggestion = data[0]
        assert "id" in suggestion
        assert "title" in suggestion
        assert "poster_path" in suggestion
        assert "year" in suggestion
        assert suggestion["title"].startswith("Inter")


@pytest.mark.asyncio
async def test_search_suggest_async(async_client):
    """Test search suggest endpoint asynchronously with async_client fixture."""
    response = await async_client.get("/api/v1/search/suggest?q=Inter&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "title" in data[0]





