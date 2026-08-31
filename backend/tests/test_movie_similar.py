import unittest
from fastapi.testclient import TestClient
from app.main import app


class MovieSimilarAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_similar_movies_endpoint(self):
        response = self.client.get("/api/v1/movie/1/similar?limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["movie_id"], "1")
        self.assertEqual(data["algorithm"], "hybrid_jaccard_similarity")
        self.assertIn("movies", data)
        self.assertIsInstance(data["movies"], list)
        
        # Verify target movie 1 is excluded from results
        movie_ids = [m["id"] for m in data["movies"]]
        self.assertNotIn("1", movie_ids)

    def test_similar_movies_not_found(self):
        response = self.client.get("/api/v1/movie/non_existent_movie_id_99999/similar")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
