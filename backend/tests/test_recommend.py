import pytest
import unittest

from app.api.v1 import recommend


class RecommendationHelpersTests(unittest.TestCase):
    def setUp(self):
        recommend._tmdb_genre_map = {
            28: "Action",
            35: "Comedy",
            878: "Science Fiction",
        }

    def tearDown(self):
        recommend._tmdb_genre_map = {}

    def test_match_score_is_deterministic(self):
        first = recommend._calculate_match_score(8.4, 750.0)
        second = recommend._calculate_match_score(8.4, 750.0)

        self.assertEqual(first, second)
        self.assertEqual(first, 0.76)

    def test_match_score_is_bounded(self):
        self.assertEqual(
            recommend._calculate_match_score(-2.0, -10.0),
            0.0,
        )
        self.assertLessEqual(
            recommend._calculate_match_score(20.0, 1_000_000.0),
            1.0,
        )

    def test_genre_ids_are_mapped_to_names(self):
        self.assertEqual(
            recommend._resolve_genres([28, 878]),
            ["Action", "Science Fiction"],
        )

    def test_unknown_genres_use_clear_fallback(self):
        self.assertEqual(
            recommend._resolve_genres([999999]),
            ["Unknown"],
        )

    def test_by_emotion_endpoint(self):
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            response = client.get("/api/v1/recommend/by-emotion?emotion=Tense&limit=5")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIn("algorithm", data)
            self.assertIn("movies", data)
            self.assertIsInstance(data["movies"], list)


@pytest.mark.asyncio
async def test_recommend_trending_async(async_client):
    """Test /api/v1/recommend/trending endpoint asynchronously with async_client fixture."""
    response = await async_client.get("/api/v1/recommend/trending?limit=5")
    assert response.status_code in (200, 503)
    data = response.json()
    if response.status_code == 200:
        assert "algorithm" in data
        assert "movies" in data
        assert isinstance(data["movies"], list)


if __name__ == "__main__":
    unittest.main()

