import unittest
from fastapi.testclient import TestClient
from app.main import app


class AnalyticsAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_track_event_endpoint_success(self):
        payload = {
            "event_type": "click",
            "movie_id": "1",
            "source": "trending"
        }
        response = self.client.post("/api/v1/analytics/event", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "queued")
        self.assertEqual(data["event_type"], "click")
        self.assertEqual(data["movie_id"], "1")

    def test_track_event_invalid_type(self):
        payload = {
            "event_type": "invalid_type",
            "movie_id": "1"
        }
        response = self.client.post("/api/v1/analytics/event", json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("Invalid event_type", data["detail"])

    def test_top_clicked_endpoint(self):
        response = self.client.get("/api/v1/analytics/top-clicked?hours=24&limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("timeframe", data)
        self.assertIn("movies", data)
        self.assertIsInstance(data["movies"], list)


if __name__ == "__main__":
    unittest.main()
