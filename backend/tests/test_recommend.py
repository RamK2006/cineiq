import pytest
from unittest import mock
import httpx
from fastapi import HTTPException

from app.main import app
from app.core.config import settings
from app.core.security import get_current_user

# Mock SVD model structures
class MockTrainset:
    def all_items(self):
        return [1, 2]
        
    def to_raw_iid(self, iid):
        return "550" if iid == 1 else "551"

class MockPrediction:
    def __init__(self, est):
        self.est = est

class MockSVDModel:
    def __init__(self):
        self.trainset = MockTrainset()
        
    def predict(self, uid, iid):
        # Return high ratings so they are selected
        return MockPrediction(4.8 if iid == "550" else 4.2)

def test_recommend_auth_rejection(client):
    """Test that personalized endpoint rejects unauthenticated requests."""
    def mock_auth_reject():
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    app.dependency_overrides[get_current_user] = mock_auth_reject
    try:
        response = client.get("/api/v1/recommend/personalized")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"
    finally:
        del app.dependency_overrides[get_current_user]

def test_recommend_personalized_success(client, monkeypatch):
    """Test personalized recommendation success when SVD and TMDB are available."""
    app.dependency_overrides[get_current_user] = lambda: "authenticated_user_777"
    monkeypatch.setattr(settings, "tmdb_api_key", "test_tmdb_key")
    
    # Mock _get_svd_model to return our MockSVDModel
    mock_model = MockSVDModel()
    monkeypatch.setattr("app.api.v1.recommend._get_svd_model", lambda: mock_model)
    
    try:
        response = client.get("/api/v1/recommend/personalized")
        assert response.status_code == 200
        data = response.json()
        assert data["algorithm"] == "svd_collaborative_filtering"
        assert len(data["movies"]) > 0
        # Check that TMDB details for mock movies were fetched
        assert data["movies"][0]["id"] == "550"
        assert "genres" in data["movies"][0]
    finally:
        del app.dependency_overrides[get_current_user]

def test_recommend_personalized_svd_unavailable_fallback(client, monkeypatch):
    """Test fallback to TMDB popular recommendations when SVD model is unavailable."""
    app.dependency_overrides[get_current_user] = lambda: "authenticated_user_777"
    monkeypatch.setattr(settings, "tmdb_api_key", "test_tmdb_key")
    
    # Force SVD model to be None (unavailable)
    monkeypatch.setattr("app.api.v1.recommend._get_svd_model", lambda: None)
    
    try:
        response = client.get("/api/v1/recommend/personalized")
        assert response.status_code == 200
        data = response.json()
        # Fallback uses hybrid_ncf_svd_mock label but fetches TMDB movies
        assert data["algorithm"] == "hybrid_ncf_svd_mock"
        assert len(data["movies"]) > 0
        assert data["movies"][0]["title"] == "Fight Club" # From popular movies mock
    finally:
        del app.dependency_overrides[get_current_user]

def test_recommend_personalized_tmdb_unavailable_fallback(client, monkeypatch):
    """Test fallback to static local mock movies when SVD and TMDB both fail/not configured."""
    app.dependency_overrides[get_current_user] = lambda: "authenticated_user_777"
    
    # Disable SVD and TMDB
    monkeypatch.setattr("app.api.v1.recommend._get_svd_model", lambda: None)
    monkeypatch.setattr(settings, "tmdb_api_key", "")
    
    try:
        response = client.get("/api/v1/recommend/personalized")
        assert response.status_code == 200
        data = response.json()
        assert data["algorithm"] == "hybrid_ncf_svd_mock"
        assert len(data["movies"]) == 2
        assert data["movies"][0]["title"] == "Inception"
        assert data["movies"][1]["title"] == "Interstellar"
    finally:
        del app.dependency_overrides[get_current_user]

def test_recommend_trending_success(client, monkeypatch):
    """Test trending endpoint returns movies from TMDB daily trending."""
    monkeypatch.setattr(settings, "tmdb_api_key", "test_tmdb_key")
    
    response = client.get("/api/v1/recommend/trending")
    assert response.status_code == 200
    data = response.json()
    assert data["algorithm"] == "trending"
    assert len(data["movies"]) == 1
    assert data["movies"][0]["title"] == "Dune: Part Two"

def test_recommend_trending_tmdb_unavailable_fallback(client, monkeypatch):
    """Test trending endpoint falls back to static movie when TMDB fails."""
    monkeypatch.setattr(settings, "tmdb_api_key", "")
    
    response = client.get("/api/v1/recommend/trending")
    assert response.status_code == 200
    data = response.json()
    assert data["algorithm"] == "trending"
    assert len(data["movies"]) == 1
    assert data["movies"][0]["title"] == "Dune: Part Two"
    assert data["movies"][0]["id"] == "3"
