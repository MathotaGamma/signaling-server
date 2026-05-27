"""
Signaling Server (Render)

/ws/{room_id}  … WebRTC シグナリング。同室全員にbroadcast（送信者除く）
/              … ヘルスチェック（Renderウォームアップ用）
/home          … 管理ページ（templates/home.html）
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR  = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# room_id -> [WebSocket, ...]
rooms: dict[str, list[WebSocket]] = {}


@app.websocket("/ws/{room_id}")
async def signaling(ws: WebSocket, room_id: str):
    await ws.accept()
    rooms.setdefault(room_id, []).append(ws)
    peers = rooms[room_id]

    # P2P用: 2人目入室時だけ {"type":"ready"} を送る
    if len(peers) > 1:
        await ws.send_text(json.dumps({"type": "ready"}))

    try:
        while True:
            data = await ws.receive_text()
            for peer in peers:
                if peer is not ws:
                    await peer.send_text(data)
    except WebSocketDisconnect:
        peers.remove(ws)
        if not peers:
            del rooms[room_id]


@app.get("/")
def health():
    """Renderウォームアップ・死活監視用。"""
    return {"status": "ok", "rooms": len(rooms)}


@app.get("/home")
def home(request: Request):
    """管理ページ。"""
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"rooms": list(rooms.keys())},
    )
