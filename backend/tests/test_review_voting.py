import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.reviews import get_current_user
from app.db.session import AsyncSessionLocal, engine
from app.db.models import Movie, Base


client = TestClient(app)


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        movie = await session.get(Movie, "movie_vote_test")
        if not movie:
            session.add(Movie(id="movie_vote_test", title="Test Movie"))
            await session.commit()
    yield

def test_review_vote_flow():
    # Setup test user and movie in DB
    user_id = "voter_user_123"
    movie_id = "movie_vote_test"
    review_id = "review_vote_test"

    app.dependency_overrides[get_current_user] = lambda: user_id


    # 1. Create a review to vote on
    create_resp = client.post(
        f"/api/v1/movies/{movie_id}/reviews",
        json={"rating": 5, "text": "Great movie!"}
    )
    if create_resp.status_code == 201:
        review_id = create_resp.json()["id"]

    # 2. Vote +1 (Helpful)
    vote_resp = client.post(f"/api/v1/reviews/{review_id}/vote", json={"vote_type": 1})
    assert vote_resp.status_code == 200
    assert vote_resp.json()["user_vote"] == 1
    assert "recorded" in vote_resp.json()["message"]

    # 3. Retract +1 (Clicking +1 again)
    retract_resp = client.post(f"/api/v1/reviews/{review_id}/vote", json={"vote_type": 1})
    assert retract_resp.status_code == 200
    assert retract_resp.json()["user_vote"] == 0
    assert "retracted" in retract_resp.json()["message"]

    # 4. Vote -1 (Unhelpful)
    unhelpful_resp = client.post(f"/api/v1/reviews/{review_id}/vote", json={"vote_type": -1})
    assert unhelpful_resp.status_code == 200
    assert unhelpful_resp.json()["user_vote"] == -1

    # 5. Flip vote from -1 to +1
    flip_resp = client.post(f"/api/v1/reviews/{review_id}/vote", json={"vote_type": 1})
    assert flip_resp.status_code == 200
    assert flip_resp.json()["user_vote"] == 1
    assert "flipped" in flip_resp.json()["message"]

    # 6. Invalid vote_type (e.g. 5)
    invalid_resp = client.post(f"/api/v1/reviews/{review_id}/vote", json={"vote_type": 5})
    assert invalid_resp.status_code == 400

    # 7. Non-existent review
    not_found_resp = client.post("/api/v1/reviews/non_existent_id/vote", json={"vote_type": 1})
    assert not_found_resp.status_code == 404

    app.dependency_overrides.clear()
