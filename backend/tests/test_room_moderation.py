import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
import json
import uuid

from app.main import app
from app.api.v1.room import get_room_meta, set_room_meta, manager, in_memory_meta, hash_passcode, verify_passcode, in_memory_messages, in_memory_state
from app.core.security import get_current_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_room_state():
    in_memory_meta.clear()
    in_memory_messages.clear()
    in_memory_state.clear()
    manager.active_connections.clear()
    yield

def test_create_room_passcode():
    app.dependency_overrides[get_current_user] = lambda: "host123"
    response = client.post("/api/v1/room/create", json={"passcode": "secret123"})
    assert response.status_code == 200
    room_id = response.json()["room_id"]
    
    meta = get_room_meta(room_id)
    assert meta["is_locked"] is True
    assert verify_passcode("secret123", meta["passcode_hash"])
    assert meta["host_id"] == "host123"
    app.dependency_overrides.clear()

def test_create_room_no_passcode():
    app.dependency_overrides[get_current_user] = lambda: "host123"
    response = client.post("/api/v1/room/create", json={})
    assert response.status_code == 200
    room_id = response.json()["room_id"]
    
    meta = get_room_meta(room_id)
    assert meta["is_locked"] is False
    assert meta["passcode_hash"] is None
    app.dependency_overrides.clear()

@patch("app.api.v1.room.verify_token")
def test_websocket_moderation(mock_verify):
    # Setup room and mock auth
    room_id = "test-room"
    host_id = "host123"
    user_id = "user456"
    
    # Create an unlocked room
    set_room_meta(room_id, {
        "host_id": host_id,
        "is_locked": False,
        "passcode_hash": None,
        "muted_users": []
    })

    # To test websockets, we need to mock verify_token to return different users based on token
    async def mock_verify_impl(credentials):
        return {"sub": credentials.credentials}
    mock_verify.side_effect = mock_verify_impl

    # Host connects
    with client.websocket_connect(f"/api/v1/room/ws/{room_id}?token={host_id}") as host_ws:
        # Host receives initial state
        msg = host_ws.receive_json()
        if msg["type"] == "sync": msg = host_ws.receive_json() # skip sync
        if msg["type"] == "history": msg = host_ws.receive_json() # skip history
        assert msg["type"] == "room_state"
        assert msg["payload"]["host_id"] == host_id
        
        # User connects
        with client.websocket_connect(f"/api/v1/room/ws/{room_id}?token={user_id}") as user_ws:
            # User receives initial state
            msg = user_ws.receive_json()
            if msg["type"] == "sync": msg = user_ws.receive_json()
            if msg["type"] == "history": msg = user_ws.receive_json()
            assert msg["type"] == "room_state"
            assert msg["payload"]["host_id"] == host_id
            
            # Host receives user_joined
            msg = host_ws.receive_json()
            assert msg["type"] == "user_joined"
            assert msg["user"] == user_id
            
            # Test 1: Non-host tries to Mute
            user_ws.send_json({"type": "MUTE_USER", "payload": {"user_id": host_id, "muted": True}})
            msg = user_ws.receive_json()
            assert msg.get("error") == "Only host can perform this action"
            
            # Test 2: Host Mutes user
            host_ws.send_json({"type": "MUTE_USER", "payload": {"user_id": user_id, "muted": True}})
            # User receives mute
            msg = user_ws.receive_json()
            assert msg["type"] == "USER_MUTED"
            # Host receives personal message
            msg = host_ws.receive_json()
            assert msg["type"] == "USER_MUTED"
            
            # Test 3: Muted user tries to chat
            user_ws.send_json({"type": "chat", "payload": {"text": "hello"}})
            msg = user_ws.receive_json()
            assert msg.get("error") == "You are muted"
            
            # Test 4: Host transfers host
            host_ws.send_json({"type": "TRANSFER_HOST", "payload": {"user_id": user_id}})
            msg = user_ws.receive_json()
            assert msg["type"] == "TRANSFER_HOST"
            
            msg = host_ws.receive_json()
            assert msg["type"] == "TRANSFER_HOST"
            
            # Test 5: Old host tries to lock room (should fail)
            host_ws.send_json({"type": "LOCK_ROOM"})
            msg = host_ws.receive_json()
            assert msg.get("error") == "Only host can perform this action"
            
            # Test 6: New host kicks old host
            user_ws.send_json({"type": "KICK_USER", "payload": {"user_id": host_id}})
            msg = host_ws.receive_json()
            assert msg["type"] == "USER_KICKED"
            
            # New host should get user_left
            msg = user_ws.receive_json()
            assert msg["type"] == "user_left"
            assert msg["user"] == host_id

@patch("app.api.v1.room.verify_token")
def test_websocket_locked_room(mock_verify):
    room_id = "locked-room"
    host_id = "host123"
    user_id = "user456"
    
    passcode_hash = hash_passcode("secret")
    set_room_meta(room_id, {
        "host_id": host_id,
        "is_locked": True,
        "passcode_hash": passcode_hash,
        "muted_users": []
    })

    async def mock_verify_impl(credentials):
        return {"sub": credentials.credentials}
    mock_verify.side_effect = mock_verify_impl

    # Host can connect without passcode
    with client.websocket_connect(f"/api/v1/room/ws/{room_id}?token={host_id}") as host_ws:
        msg = host_ws.receive_json()
        if msg["type"] == "sync": msg = host_ws.receive_json()
        if msg["type"] == "history": msg = host_ws.receive_json()
        assert msg["type"] == "room_state"

    # User connects and gets prompted for passcode
    with client.websocket_connect(f"/api/v1/room/ws/{room_id}?token={user_id}") as user_ws:
        msg = user_ws.receive_json()
        assert msg["type"] == "PASSCODE_REQUIRED"
        
        # Wrong passcode
        user_ws.send_json({"type": "submit_passcode", "payload": {"passcode": "wrong"}})
        msg = user_ws.receive_json()
        assert msg["type"] == "PASSCODE_REJECTED"
        
        # Correct passcode
        user_ws.send_json({"type": "submit_passcode", "payload": {"passcode": "secret"}})
        msg = user_ws.receive_json()
        assert msg["type"] == "PASSCODE_ACCEPTED"
        
        # Then receives state
        msg = user_ws.receive_json()
        if msg["type"] == "sync": msg = user_ws.receive_json()
        if msg["type"] == "history": msg = user_ws.receive_json()
        assert msg["type"] == "room_state"
