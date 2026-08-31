"""Tests for the personal Watchlist / Favorites endpoints (issue #279)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import get_current_user
from app.db.session import AsyncSessionLocal, engine
from app.db.models import Movie, Base


client = TestClient(app)

MOVIE_ID = "user_action_movie"
PAGINATION_MOVIES = [f"user_action_pag_{i}" for i in range(1, 6)]


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        if not await session.get(Movie, MOVIE_ID):
            session.add(Movie(id=MOVIE_ID, title="User Action Movie"))
        for movie_id in PAGINATION_MOVIES:
            if not await session.get(Movie, movie_id):
                session.add(Movie(id=movie_id, title="Pagination Movie"))
        await session.commit()
    yield
    app.dependency_overrides.clear()


def _login(user_id: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: user_id


# ─── Auth ───────────────────────────────────────────────────────────────────


def test_user_endpoints_require_auth():
    """Watchlist/favorites endpoints must reject unauthenticated requests."""
    assert client.get("/api/v1/user/watchlist").status_code in (401, 403, 503)
    assert client.get("/api/v1/user/favorites").status_code in (401, 403, 503)
    assert (
        client.post(f"/api/v1/user/watchlist/{MOVIE_ID}").status_code
        in (401, 403, 503)
    )


# ─── Watchlist ───────────────────────────────────────────────────────────────


def test_watchlist_add_list_remove():
    user_id = "watchlist_user_1"
    _login(user_id)

    # Add
    resp = client.post(f"/api/v1/user/watchlist/{MOVIE_ID}")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["action"]["movie"]["id"] == MOVIE_ID
    assert body["action"]["added_at"]

    # Listed with movie details
    resp = client.get("/api/v1/user/watchlist")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["pages"] == 1
    assert data["items"][0]["movie"]["id"] == MOVIE_ID
    assert data["items"][0]["movie"]["title"] == "User Action Movie"

    # Idempotent re-add
    resp = client.post(f"/api/v1/user/watchlist/{MOVIE_ID}")
    assert resp.status_code == 200
    assert "Already" in resp.json()["message"]

    # Remove
    resp = client.delete(f"/api/v1/user/watchlist/{MOVIE_ID}")
    assert resp.status_code == 200, resp.text

    # Empty list afterwards
    data = client.get("/api/v1/user/watchlist").json()
    assert data["total"] == 0
    assert data["items"] == []

    # Removing again → 404
    assert client.delete(f"/api/v1/user/watchlist/{MOVIE_ID}").status_code == 404


def test_watchlist_unknown_movie_404():
    _login("watchlist_user_2")
    resp = client.post("/api/v1/user/watchlist/does_not_exist")
    assert resp.status_code == 404
    # Nothing was persisted
    assert client.get("/api/v1/user/watchlist").json()["total"] == 0


def test_watchlist_isolation_between_users():
    _login("watchlist_user_3")
    client.post(f"/api/v1/user/watchlist/{MOVIE_ID}")
    total_for_user_3 = client.get("/api/v1/user/watchlist").json()["total"]
    assert total_for_user_3 == 1

    _login("watchlist_user_4")
    assert client.get("/api/v1/user/watchlist").json()["total"] == 0
    # User 4 removes it → 404 (not present in THEIR list)
    assert client.delete(f"/api/v1/user/watchlist/{MOVIE_ID}").status_code == 404
    # User 3's entry is untouched
    _login("watchlist_user_3")
    assert client.get("/api/v1/user/watchlist").json()["total"] == 1


def test_watchlist_pagination():
    user_id = "watchlist_user_5"
    _login(user_id)

    for movie_id in PAGINATION_MOVIES:
        assert client.post(f"/api/v1/user/watchlist/{movie_id}").status_code == 201

    # Page 1 of 2 per page
    data = client.get("/api/v1/user/watchlist?page=1&limit=2").json()
    assert data["total"] == 5
    assert data["pages"] == 3
    assert len(data["items"]) == 2
    assert {item["movie"]["id"] for item in data["items"]} <= set(PAGINATION_MOVIES)

    # Last page has the remainder
    data = client.get("/api/v1/user/watchlist?page=3&limit=2").json()
    assert len(data["items"]) == 1

    # No duplicates across pages
    seen = set()
    for page in (1, 2, 3):
        for item in client.get(
            f"/api/v1/user/watchlist?page={page}&limit=2"
        ).json()["items"]:
            assert item["movie"]["id"] not in seen
            seen.add(item["movie"]["id"])
    assert len(seen) == 5


# ─── Favorites ───────────────────────────────────────────────────────────────


def test_favorites_add_list_remove():
    user_id = "favorites_user_1"
    _login(user_id)

    resp = client.post(f"/api/v1/user/favorites/{MOVIE_ID}")
    assert resp.status_code == 201, resp.text
    assert resp.json()["action"]["movie"]["id"] == MOVIE_ID

    # Idempotent
    resp = client.post(f"/api/v1/user/favorites/{MOVIE_ID}")
    assert resp.status_code == 200
    assert "Already" in resp.json()["message"]

    # Listed
    data = client.get("/api/v1/user/favorites").json()
    assert data["total"] == 1
    assert data["items"][0]["movie"]["id"] == MOVIE_ID

    # Watchlist is a separate collection
    assert client.get("/api/v1/user/watchlist").json()["total"] == 0

    # Remove
    assert client.delete(f"/api/v1/user/favorites/{MOVIE_ID}").status_code == 200
    assert client.get("/api/v1/user/favorites").json()["total"] == 0
    assert client.delete(f"/api/v1/user/favorites/{MOVIE_ID}").status_code == 404


def test_favorites_unknown_movie_404():
    _login("favorites_user_2")
    resp = client.post("/api/v1/user/favorites/does_not_exist")
    assert resp.status_code == 404
    assert client.get("/api/v1/user/favorites").json()["total"] == 0


def test_same_movie_can_be_in_both_collections():
    """Watchlist and favorite are independent actions on the same movie."""
    _login("both_collections_user")

    assert client.post(f"/api/v1/user/watchlist/{MOVIE_ID}").status_code == 201
    assert client.post(f"/api/v1/user/favorites/{MOVIE_ID}").status_code == 201

    assert client.get("/api/v1/user/watchlist").json()["total"] == 1
    assert client.get("/api/v1/user/favorites").json()["total"] == 1

    # Removing one leaves the other intact
    assert client.delete(f"/api/v1/user/watchlist/{MOVIE_ID}").status_code == 200
    assert client.get("/api/v1/user/watchlist").json()["total"] == 0
    assert client.get("/api/v1/user/favorites").json()["total"] == 1
