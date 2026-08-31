from fastapi.testclient import TestClient


from app.main import app
from app.api.v1.profile import compute_taste_radar, MOCK_WATCH_HISTORY
from app.core.security import get_current_user

client = TestClient(app)

def test_compute_taste_radar_algorithm():
    radar_data, summary_msg = compute_taste_radar(MOCK_WATCH_HISTORY)
    
    assert len(radar_data) > 0
    assert len(radar_data) <= 6
    
    # Verify structure of each RadarItem
    for item in radar_data:
        assert hasattr(item, "subject")
        assert hasattr(item, "A")
        assert 0 <= item.A <= 100
        assert item.fullMark == 100

    # Top genre (Sci-Fi) should have 100% normalized score
    top_item = radar_data[0]
    assert top_item.subject == "Sci-Fi"
    assert top_item.A == 100

    # Contextual summary message format verification
    assert "Your taste profile leans heavily toward" in summary_msg
    assert "Sci-Fi (100%)" in summary_msg

def test_fetch_profile_stats_endpoint():
    app.dependency_overrides[get_current_user] = lambda: "user_test_analytics"
    
    response = client.get("/api/v1/profile/stats")
    assert response.status_code == 200
    
    data = response.json()
    assert "radarData" in data
    assert "summaryMessage" in data
    assert isinstance(data["radarData"], list)
    assert len(data["radarData"]) > 0
    assert "Your taste profile leans heavily toward" in data["summaryMessage"]
    
    app.dependency_overrides.clear()
