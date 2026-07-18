import pytest
from fastapi import status
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

from app.core.config import settings

def test_create_room(client):
    """Test room creation endpoint."""
    response = client.post("/api/v1/room/create")
    assert response.status_code == 200
    data = response.json()
    assert "room_id" in data
    assert data["status"] == "created"

def test_room_websocket_invalid_json(client):
    """Test that sending invalid JSON to room WS returns formatted error."""
    room_id = "test_room_invalid_json"
    with client.websocket_connect(f"/api/v1/room/ws/{room_id}") as websocket:
        websocket.send_text("not-a-json-string")
        response = websocket.receive_json()
        assert response == {"error": "Invalid JSON format"}

def test_room_websocket_invalid_schema(client):
    """Test that sending invalid schema/message type returns schema validation error."""
    room_id = "test_room_invalid_schema"
    with client.websocket_connect(f"/api/v1/room/ws/{room_id}") as websocket:
        # Invalid 'type' literal value
        websocket.send_json({"type": "dance", "payload": {}})
        response = websocket.receive_json()
        assert response["error"] == "Invalid message schema"
        assert "details" in response

def test_room_websocket_broadcast(client):
    """Test that room WS broadcasts events to other participants except the sender."""
    room_id = "sync_room_xyz"
    
    # Connect two clients to the same room
    with client.websocket_connect(f"/api/v1/room/ws/{room_id}") as ws1:
        with client.websocket_connect(f"/api/v1/room/ws/{room_id}") as ws2:
            # ws1 sends a sync action
            ws1.send_json({"type": "play", "payload": {"timestamp": 12.34}})
            
            # ws2 should receive the broadcast
            broadcast_msg = ws2.receive_json()
            assert broadcast_msg["type"] == "play"
            assert broadcast_msg["payload"]["timestamp"] == 12.34
            
            # Send message back from ws2 to ws1
            ws2.send_json({"type": "pause"})
            broadcast_msg_ws1 = ws1.receive_json()
            assert broadcast_msg_ws1["type"] == "pause"

def test_room_websocket_max_participants_rejected(client, monkeypatch):
    """Test that connections beyond max participants are rejected with code 1008."""
    # Set maximum room participants to 1 for this test
    monkeypatch.setattr(settings, "max_room_participants", 1)
    room_id = "full_room_123"
    
    # Connect the first client (should be allowed)
    with client.websocket_connect(f"/api/v1/room/ws/{room_id}") as ws1:
        # Attempt to connect the second client (should be rejected)
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(f"/api/v1/room/ws/{room_id}"):
                pass
        
        assert excinfo.value.code == 1008
        # Starlette/FastAPI websocket disconnect reason verification
        # The exception object might store the reason if provided by server
