import json
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_room_live_chat_and_presence():
    room_id = "test_chat_room_101"
    user1 = "user_alpha_1"
    user2 = "user_beta_2"

    # Connect user 1
    with client.websocket_connect(f"/ws/room/{room_id}/{user1}?username=AlphaUser") as ws1:
        # Hydration message for user 1
        raw_hyd1 = ws1.receive_text()
        hyd1 = json.loads(raw_hyd1)
        assert hyd1["type"] == "ROOM_HYDRATION"
        assert len(hyd1["data"]["members"]) == 1
        assert hyd1["data"]["members"][0]["username"] == "AlphaUser"

        # Connect user 2
        with client.websocket_connect(f"/ws/room/{room_id}/{user2}?username=BetaUser") as ws2:
            # Hydration message for user 2
            raw_hyd2 = ws2.receive_text()
            hyd2 = json.loads(raw_hyd2)
            assert hyd2["type"] == "ROOM_HYDRATION"
            assert len(hyd2["data"]["members"]) == 2

            # User 1 receives USER_JOINED and peer-joined for User 2
            raw_a = ws1.receive_text()
            raw_b = ws1.receive_text()
            evt_a = json.loads(raw_a)
            evt_b = json.loads(raw_b)
            evts = {evt_a["type"]: evt_a, evt_b["type"]: evt_b}
            assert "USER_JOINED" in evts
            assert "peer-joined" in evts
            assert evts["USER_JOINED"]["data"]["userId"] == user2


            # User 1 sends a chat message
            ws1.send_text(json.dumps({
                "type": "CHAT_MESSAGE",
                "data": {"text": "Hello Watch Party!", "timestamp": "12:00 PM"}
            }))

            # User 1 and User 2 receive the chat message
            msg1 = json.loads(ws1.receive_text())
            msg2 = json.loads(ws2.receive_text())
            assert msg1["type"] == "CHAT_MESSAGE"
            assert msg1["data"]["text"] == "Hello Watch Party!"
            assert msg2["type"] == "CHAT_MESSAGE"
            assert msg2["data"]["text"] == "Hello Watch Party!"

            # User 2 sends an emoji reaction
            ws2.send_text(json.dumps({
                "type": "EMOJI_REACTION",
                "data": {"emoji": "🍿"}
            }))

            # Both receive EMOJI_REACTION packet
            emo1 = json.loads(ws1.receive_text())
            emo2 = json.loads(ws2.receive_text())
            assert emo1["type"] == "EMOJI_REACTION"
            assert emo1["data"]["emoji"] == "🍿"
            assert emo2["type"] == "EMOJI_REACTION"
            assert emo2["data"]["emoji"] == "🍿"
