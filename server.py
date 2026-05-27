"""
Signaling Server (Render)
WebRTCのシグナリングのみ。ゲームデータ・チャットは全てP2P直通。

/ws/{room_id}  … シグナリング。同室の全員にbroadcast（送信者除く）
                  サーバーは内容を解釈しない。
/              … ヘルスチェック（Renderウォームアップ用）
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pathlib import Path
import json

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = Path(__file__).resolve().parent
print(str(BASE_DIR))

templates = Jinja2Templates(
    directory=str(BASE_DIR / "templates")
)

# room_id -> [WebSocket, ...]
rooms: dict[str, list[WebSocket]] = {}

@app.websocket("/ws/{room_id}")
async def signaling(ws: WebSocket, room_id: str):
    await ws.accept()
    rooms.setdefault(room_id, []).append(ws)
    peers = rooms[room_id]

    # 2人目以降に "ready" を送って既存メンバーにネゴシエーション開始を促す
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
def root():
    return {"status": "ok", "rooms": list(rooms.keys())}

@app.get("/home")
def root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})
    
"""
WebRTC Signaling Server
Render deployment: FastAPI + WebSocket
"""

"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import json

templates = Jinja2Templates(directory="templates")

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

@app.get("/home")
def root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})
"""
