"""
WebRTC Signaling Server
Render deployment: FastAPI + WebSocket
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# room_id -> list of WebSocket
rooms: dict[str, list[WebSocket]] = {}


@app.websocket("/ws/{room_id}")
async def signaling(ws: WebSocket, room_id: str):
    await ws.accept()
    rooms.setdefault(room_id, []).append(ws)
    peers = rooms[room_id]

    # 既存ピアに新規参加を通知
    if len(peers) > 1:
        await ws.send_text(json.dumps({"type": "ready"}))

    try:
        while True:
            data = await ws.receive_text()
            # 同室の他全員に転送
            for peer in peers:
                if peer is not ws:
                    await peer.send_text(data)
    except WebSocketDisconnect:
        peers.remove(ws)
        if not peers:
            del rooms[room_id]


@app.get("/")
def root():
    return {"status": "ok", "rooms": list(rooms.keys())}
