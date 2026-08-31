import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Movie, Review


@pytest.mark.asyncio
async def test_get_movie_reviews_empty(async_client: AsyncClient):
    """Test GET /api/v1/movies/{movie_id}/reviews returns empty list when no reviews exist."""
    response = await async_client.get("/api/v1/movies/1/reviews")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "average_rating" in data
    assert "rating_count" in data
    assert data["items"] == []
    assert data["rating_count"] == 0


@pytest.mark.asyncio
async def test_create_review_unauthenticated(async_client: AsyncClient):
    """Test POST /api/v1/movies/{movie_id}/reviews fails without authentication header."""
    payload = {
        "rating": 5,
        "text": "Amazing movie!"
    }
    response = await async_client.post("/api/v1/movies/1/reviews", json=payload)
    # Protected endpoint returns 401 or 503 if Clerk is unconfigured
    assert response.status_code in (401, 503)


@pytest.mark.asyncio
async def test_get_movie_reviews_with_data(
    async_client: AsyncClient,
    test_db_session: AsyncSession
):
    """Test GET /api/v1/movies/{movie_id}/reviews returns seeded reviews."""
    # Seed movie and review
    movie = Movie(
        id="test_movie_1",
        title="Test Movie",
        overview="Test Overview",
        genres=["Action"]
    )
    review = Review(
        id="review_1",
        user_id="user_1",
        movie_id="test_movie_1",
        rating=4,
        text="Great film"
    )
    test_db_session.add(movie)
    test_db_session.add(review)
    await test_db_session.commit()

    response = await async_client.get("/api/v1/movies/test_movie_1/reviews")
    assert response.status_code == 200
    data = response.json()
    assert data["rating_count"] == 1
    assert data["average_rating"] == 4.0
    assert len(data["items"]) == 1
    assert data["items"][0]["text"] == "Great film"

