import pytest
from fastapi.testclient import TestClient
import json

from app.main import app
from app.api.v1.room import ROOM_SIGNALING_REGISTRY

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_signaling_registry():
    ROOM_SIGNALING_REGISTRY.clear()
    yield
    ROOM_SIGNALING_REGISTRY.clear()

def test_webrtc_signaling_peer_connection_flow():
    room_id = "test-room-mesh-1"
    user1 = "user1"
    user2 = "user2"

    # User 1 connects
    with client.websocket_connect(f"/ws/room/{room_id}/{user1}") as ws1:
        assert room_id in ROOM_SIGNALING_REGISTRY
        assert user1 in ROOM_SIGNALING_REGISTRY[room_id]

        # User 2 connects
        with client.websocket_connect(f"/ws/room/{room_id}/{user2}") as ws2:
            assert user2 in ROOM_SIGNALING_REGISTRY[room_id]

            # ws1 should receive peer-joined message for user2
            data1 = ws1.receive_json()
            assert data1["type"] == "peer-joined"
            assert data1["peerId"] == user2

            # User 1 sends WebRTC offer
            offer_payload = {"type": "offer", "data": {"sdp": "fake_sdp_offer"}}
            ws1.send_json(offer_payload)

            # User 2 should receive offer
            data2 = ws2.receive_json()
            assert data2["type"] == "offer"
            assert data2["senderId"] == user1
            assert data2["data"]["sdp"] == "fake_sdp_offer"

            # User 2 sends WebRTC answer
            answer_payload = {"type": "answer", "data": {"sdp": "fake_sdp_answer"}}
            ws2.send_json(answer_payload)

            # User 1 should receive answer
            resp1 = ws1.receive_json()
            assert resp1["type"] == "answer"
            assert resp1["senderId"] == user2
            assert resp1["data"]["sdp"] == "fake_sdp_answer"

            # User 1 sends ICE candidate
            candidate_payload = {"type": "ice-candidate", "data": {"candidate": "fake_candidate"}}
            ws1.send_json(candidate_payload)

            # User 2 should receive candidate
            cand_resp = ws2.receive_json()
            assert cand_resp["type"] == "ice-candidate"
            assert cand_resp["senderId"] == user1
            assert cand_resp["data"]["candidate"] == "fake_candidate"

        # User 2 disconnects, User 1 receives peer-left
        left_msg = ws1.receive_json()
        assert left_msg["type"] == "peer-left"
        assert left_msg["peerId"] == user2

from starlette.websockets import WebSocketDisconnect

def test_webrtc_signaling_capacity_limit():
    room_id = "test-room-mesh-capacity"
    
    # Connect 4 users successfully
    with client.websocket_connect(f"/ws/room/{room_id}/user1") as ws1, \
         client.websocket_connect(f"/ws/room/{room_id}/user2") as ws2, \
         client.websocket_connect(f"/ws/room/{room_id}/user3") as ws3, \
         client.websocket_connect(f"/ws/room/{room_id}/user4") as ws4:
        
        assert len(ROOM_SIGNALING_REGISTRY[room_id]) == 4

        # Attempting 5th user connection should fail with code 4001
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws/room/{room_id}/user5") as ws5:
                ws5.receive_text()
        assert exc_info.value.code == 4001


