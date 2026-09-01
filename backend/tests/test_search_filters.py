"""Structured search filters (issue #274). Seeded catalogue:

    id     title            genres               year  rating  popularity
    sf01   Nebula Drift     Sci-Fi, Action       1995   8.0     100
    sf02   Time Weave       Sci-Fi, Drama        2001   7.5      50
    sf03   Steel Horizon    Action               2012   6.0     200
    sf04   Quiet Years      Drama, Romance       1988   9.0      10
    sf05   Galaxy Storm     Sci-Fi               2024   5.0     300
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import AsyncSessionLocal, engine
from app.db.models import Movie, Base
from app.api.v1.search import build_filtered_movie_query


client = TestClient(app)

CATALOGUE = {
    "sf01": ("Nebula Drift", ["Sci-Fi", "Action"], 1995, 8.0, 100.0),
    "sf02": ("Time Weave", ["Sci-Fi", "Drama"], 2001, 7.5, 50.0),
    "sf03": ("Steel Horizon", ["Action"], 2012, 6.0, 200.0),
    "sf04": ("Quiet Years", ["Drama", "Romance"], 1988, 9.0, 10.0),
    "sf05": ("Galaxy Storm", ["Sci-Fi"], 2024, 5.0, 300.0),
}


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        for movie_id, (title, genres, year, rating, popularity) in CATALOGUE.items():
            existing = await session.get(Movie, movie_id)
            if existing is None:
                session.add(
                    Movie(
                        id=movie_id,
                        title=title,
                        genres=genres,
                        release_date=datetime(year, 6, 1),
                        vote_average=rating,
                        popularity=popularity,
                        overview="A test movie.",
                    )
                )
        await session.commit()
    yield
    # Cleanup: shared persistent dev DB.
    async with AsyncSessionLocal() as session:
        for movie_id in CATALOGUE:
            movie = await session.get(Movie, movie_id)
            if movie is not None:
                await session.delete(movie)
        await session.commit()


def _search(params: dict) -> list[str]:
    """Run /search/semantic with empty q (pure structured-filter mode) and
    return the ordered list of movie ids."""
    query = dict(params)
    query.setdefault("q", "")
    response = client.get("/api/v1/search/semantic", params=query)
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["results"]]




def test_genres_single():
    assert set(_search({"genres": "Sci-Fi"})) == {"sf01", "sf02", "sf05"}


def test_genres_multiple_require_all():
    """Multiple genres are ANDed: movie must contain every listed genre."""
    assert _search({"genres": ["Sci-Fi", "Drama"]}) == ["sf02"]


def test_genres_no_match():
    assert _search({"genres": "Horror"}) == []




def test_year_range():
    assert set(_search({"year_min": 1990, "year_max": 2010})) == {"sf01", "sf02"}


def test_year_min_only():
    assert set(_search({"year_min": 2010})) == {"sf03", "sf05"}


def test_year_max_only():
    assert set(_search({"year_max": 1995})) == {"sf01", "sf04"}


def test_legacy_year_aliases_still_work():
    """The deployed frontend still sends year_from/year_to — keep accepting them."""
    legacy = set(_search({"year_from": 1990, "year_to": 2010}))
    assert legacy == {"sf01", "sf02"}
    # Canonical names take precedence per dimension when both are provided.
    assert set(_search({"year_from": 1990, "year_min": 2020, "year_to": 2100})) == {"sf05"}




def test_min_rating():
    assert _search({"min_rating": 8.5}) == ["sf04"]


def test_min_rating_boundary_inclusive():
    assert set(_search({"min_rating": 8.0})) == {"sf01", "sf04"}




def test_combined_filters():
    assert _search({"genres": "Sci-Fi", "year_min": 2000, "year_max": 2010}) == ["sf02"]


def test_combined_filters_all_dimensions():
    assert set(
        _search({"genres": "Sci-Fi", "year_min": 1990, "year_max": 2010, "min_rating": 7.0})
    ) == {"sf01", "sf02"}


def test_combined_filters_no_match():
    assert _search({"genres": "Sci-Fi", "year_max": 1990}) == []




def test_sort_popularity():
    assert _search({"sort_by": "popularity"}) == ["sf05", "sf03", "sf01", "sf02", "sf04"]


def test_sort_rating():
    assert _search({"sort_by": "rating"}) == ["sf04", "sf01", "sf02", "sf03", "sf05"]


def test_sort_year_desc():
    assert _search({"sort_by": "year_desc"}) == ["sf05", "sf03", "sf02", "sf01", "sf04"]


def test_sort_relevance_default_with_query():
    """Default sort is relevance: the title match ranks first end-to-end
    (the hybrid/keyword paths both honor it)."""
    response = client.get("/api/v1/search/semantic", params={"q": "quiet", "limit": 10})
    assert response.status_code == 200, response.text
    ids = [item["id"] for item in response.json()["results"]]
    assert ids[0] == "sf04"


def test_relevance_with_filters_excludes_non_matching():
    """q='nebula' + genres=Drama must yield nothing (Nebula Drift is not Drama)."""
    assert _search({"q": "nebula", "genres": "Drama"}) == []




@pytest.mark.parametrize(
    "params",
    [
        {"year_min": 1800},
        {"year_max": 2200},
        {"year_min": 2500},
        {"min_rating": 11.0},
        {"min_rating": -0.5},
        {"sort_by": "bogus"},
        {"year_from": 1500},
    ],
)
def test_invalid_filter_params_rejected(params):
    response = client.get("/api/v1/search/semantic", params={"q": "", **params})
    assert response.status_code == 422




@pytest.mark.asyncio
async def test_sql_builder_filters_and_relevance_ordering():
    """Direct unit test of the dynamic WHERE/ORDER construction, including
    title-match-first relevance ordering (the endpoint's hybrid path shadows
    the SQL path whenever q is non-empty, so test the builder directly)."""
    stmt = build_filtered_movie_query(
        words=["quiet"],
        genres=["Drama"],
        year_min=1980,
        year_max=2000,
        min_rating=7.0,
        sort_by="relevance",
        limit=10,
    )
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(stmt)).scalars().all()
    assert [m.id for m in rows] == ["sf04"]


    stmt = build_filtered_movie_query(
        words=["test"],
        genres=None,
        year_min=None,
        year_max=None,
        min_rating=None,
        sort_by="relevance",
        limit=10,
    )
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(stmt)).scalars().all()
    # All overviews match 'test', none of the titles do -> popularity order.
    assert [m.id for m in rows] == ["sf05", "sf03", "sf01", "sf02", "sf04"]


    stmt = build_filtered_movie_query(
        words=["nebula"],
        genres=None,
        year_min=None,
        year_max=None,
        min_rating=None,
        sort_by="relevance",
        limit=10,
    )
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(stmt)).scalars().all()
    assert rows[0].id == "sf01"
