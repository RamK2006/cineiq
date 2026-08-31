import pytest
import asyncio
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import patch, MagicMock

# Assuming we can import the router and manager from the app
from app.api.v1.room import router, manager, get_room_meta, set_room_meta, in_memory_state
from app.main import app

client = TestClient(app)

@pytest.fixture
def mock_redis():
    with patch("app.api.v1.room.get_redis") as mock_get_redis:
        mock_redis_instance = MagicMock()
        mock_get_redis.return_value = mock_redis_instance
        yield mock_redis_instance

@pytest.fixture
def mock_verify_token():
    with patch("app.api.v1.room.verify_token") as mock_verify:
        mock_verify.return_value = {"sub": "test_user_1"}
        yield mock_verify

@pytest.mark.asyncio
async def test_create_room(mock_redis):
    # Mocking depends get_current_user
    with patch("app.api.v1.room.get_current_user", return_value="host_user"):
        response = client.post("/api/v1/room/create", json={"passcode": "secret"})
        assert response.status_code == 200
        data = response.json()
        assert "room_id" in data
        assert data["status"] == "created"

@pytest.mark.asyncio
async def test_websocket_ping_pong_ntp(mock_verify_token, mock_redis):
    # Testing the NTP clock sync functionality
    room_id = "test_room_ntp"
    set_room_meta(room_id, {"host_id": "test_user_1", "is_locked": False, "passcode_hash": None, "muted_users": []})
    
    with client.websocket_connect(f"/api/v1/room/ws/{room_id}?token=valid_token") as websocket:
        # Ignore initial sync messages
        websocket.receive_json() # sync
        websocket.receive_json() # history
        websocket.receive_json() # room_state
        
        # Send PING
        client_time = 1600000000000
        websocket.send_json({"type": "PING", "payload": {"client_time": client_time}})
        
        # Expect PONG
        response = websocket.receive_json()
        assert response["type"] == "PONG"
        assert response["payload"]["client_time"] == client_time
        assert "server_time" in response["payload"]

@pytest.mark.asyncio
async def test_host_controls_playback(mock_verify_token, mock_redis):
    room_id = "test_room_playback"
    # test_user_1 is the host
    set_room_meta(room_id, {"host_id": "test_user_1", "is_locked": False, "passcode_hash": None, "muted_users": []})
    
    with client.websocket_connect(f"/api/v1/room/ws/{room_id}?token=valid_token") as websocket:
        # Ignore initial messages
        websocket.receive_json()
        websocket.receive_json()
        websocket.receive_json()
        
        # Host sends PLAY
        websocket.send_json({"type": "play", "payload": {"progress": 10.5}})
        
        # Since it's the host, it should broadcast back
        # Actually in testclient with 1 connection, broadcast sends to others, but we don't see it on the sender.
        # But we can verify it sets the state in redis
        assert mock_redis.set.called
        call_args = mock_redis.set.call_args[0]
        assert f"room:{room_id}:state" in call_args[0]
        assert "play" in call_args[1]

@pytest.mark.asyncio
async def test_non_host_denied_playback(mock_verify_token, mock_redis):
    room_id = "test_room_denied"
    # test_user_1 is NOT the host
    set_room_meta(room_id, {"host_id": "another_user", "is_locked": False, "passcode_hash": None, "muted_users": []})
    
    with client.websocket_connect(f"/api/v1/room/ws/{room_id}?token=valid_token") as websocket:
        # Ignore initial messages
        websocket.receive_json()
        websocket.receive_json()
        websocket.receive_json()
        
        # Non-host sends PLAY
        websocket.send_json({"type": "play", "payload": {"progress": 10.5}})
        
        # Expect HOST_ACTION_DENIED
        response = websocket.receive_json()
        assert response["type"] == "HOST_ACTION_DENIED"
        assert "Only the host can control" in response["error"]

@pytest.mark.asyncio
async def test_request_sync(mock_verify_token, mock_redis):
    room_id = "test_room_sync"
    set_room_meta(room_id, {"host_id": "test_user_1", "is_locked": False, "passcode_hash": None, "muted_users": []})
    mock_redis.get.return_value = '{"action": "play", "progress": 55.5, "timestamp": 1000}'
    
    with client.websocket_connect(f"/api/v1/room/ws/{room_id}?token=valid_token") as websocket:
        # Ignore initial messages
        websocket.receive_json()
        websocket.receive_json()
        websocket.receive_json()
        
        # Send REQUEST_SYNC
        websocket.send_json({"type": "REQUEST_SYNC", "payload": {}})
        
        # Expect SYNC_TIME
        response = websocket.receive_json()
        assert response["type"] == "SYNC_TIME"
        assert response["payload"]["action"] == "play"
        assert response["payload"]["progress"] == 55.5
