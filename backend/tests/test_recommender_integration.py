import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import get_current_user

def test_personalized_recommendations_cold_start():
    # Mock get_current_user to return a cold start user
    app.dependency_overrides[get_current_user] = lambda: "cold_user"
    
    # Mock Redis to return None (no cache)
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    
    with patch("app.api.v1.recommend.get_redis", return_value=mock_redis):
        client = TestClient(app)
        response = client.get("/api/v1/recommend/personalized")
        assert response.status_code == 200
        data = response.json()
        assert "algorithm" in data
        assert data["algorithm"] in ["popularity_rank_fallback", "cold_start_fallback"]
        assert "movies" in data

def test_personalized_recommendations_warm_user():
    # Mock get_current_user to return a warm user
    app.dependency_overrides[get_current_user] = lambda: "warm_user"
    
    # Mock Redis to return precomputed recommendations
    mock_redis = MagicMock()
    cached_recs = [
        {
            "id": "1",
            "title": "Interstellar",
            "poster_path": "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
            "vote_average": 8.7,
            "genres": ["Adventure", "Sci-Fi"],
            "match_score": 0.95
        }
    ]
    mock_redis.get.return_value = json.dumps(cached_recs)
    
    with patch("app.api.v1.recommend.get_redis", return_value=mock_redis):
        client = TestClient(app)
        response = client.get("/api/v1/recommend/personalized")
        assert response.status_code == 200
        data = response.json()
        assert data["algorithm"] == "collaborative_filtering_redis"
        assert len(data["movies"]) == 1
        assert data["movies"][0]["title"] == "Interstellar"
        assert data["movies"][0]["match_score"] == 0.95

    # Clean up override
    app.dependency_overrides.pop(get_current_user, None)
