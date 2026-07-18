import pytest
from unittest import mock
import httpx
import sys
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

@pytest.fixture
def client():
    """FastAPI synchronous TestClient wrapper with lifespan activation."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
async def async_client():
    """FastAPI asynchronous Client wrapper."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock_client = mock.MagicMock()
    mock_client.ping.return_value = True
    with mock.patch("app.db.session.get_redis", return_value=mock_client):
        yield mock_client

@pytest.fixture(autouse=True)
def mock_external_apis():
    """Mock all external HTTP calls (TMDB, Clerk) and Gemini SDK."""
    
    # Define custom mock for httpx.AsyncClient.get
    async def mock_get(self, url, *args, **kwargs):
        mock_resp = mock.MagicMock(spec=httpx.Response)
        
        # Check domain and endpoint
        if "api.themoviedb.org" in url:
            if "movie/popular" in url:
                mock_resp.status_code = 200
                mock_resp.json = lambda: {
                    "results": [
                        {
                            "id": 101,
                            "title": "Fight Club",
                            "poster_path": "/fight_club.jpg",
                            "vote_average": 8.4
                        },
                        {
                            "id": 102,
                            "title": "Pulp Fiction",
                            "poster_path": "/pulp_fiction.jpg",
                            "vote_average": 8.9
                        }
                    ]
                }
            elif "trending/movie/day" in url:
                mock_resp.status_code = 200
                mock_resp.json = lambda: {
                    "results": [
                        {
                            "id": 201,
                            "title": "Dune: Part Two",
                            "poster_path": "/dune2.jpg",
                            "vote_average": 8.3
                        }
                    ]
                }
            elif "search/movie" in url:
                mock_resp.status_code = 200
                mock_resp.json = lambda: {
                    "results": [
                        {
                            "id": 301,
                            "title": "Inception",
                            "overview": "A dark sci-fi movie about dream sharing",
                            "poster_path": "/inception.jpg",
                            "vote_average": 8.8
                        }
                    ]
                }
            elif "/movie/" in url:
                movie_id = url.split("/movie/")[-1].split("?")[0]
                mock_resp.status_code = 200
                mock_resp.json = lambda: {
                    "id": int(movie_id) if movie_id.isdigit() else 550,
                    "title": f"Mock Movie {movie_id}",
                    "poster_path": f"/poster_{movie_id}.jpg",
                    "vote_average": 8.0,
                    "genres": [{"name": "Sci-Fi"}, {"name": "Adventure"}]
                }
            else:
                mock_resp.status_code = 404
                mock_resp.json = lambda: {"status_message": "Not Found"}
                
        elif "api.clerk.com" in url:
            mock_resp.status_code = 200
            mock_resp.json = lambda: {
                "keys": [
                    {
                        "kid": "test_kid",
                        "kty": "RSA",
                        "use": "sig",
                        "n": "test_n",
                        "e": "AQAB"
                    }
                ]
            }
        else:
            mock_resp.status_code = 404
            mock_resp.json = lambda: {"error": "not found"}
            
        return mock_resp

    # Mock Gemini (google.generativeai)
    class MockResponse:
        def __init__(self, text):
            self.text = text

    class MockModel:
        def __init__(self, model_name):
            self.model_name = model_name
        def generate_content(self, prompt):
            return MockResponse("inception dark sci-fi")

    with mock.patch("httpx.AsyncClient.get", mock_get), \
         mock.patch("google.generativeai.GenerativeModel", MockModel), \
         mock.patch("google.generativeai.configure"):
        yield
