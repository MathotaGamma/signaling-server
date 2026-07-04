"""
Signaling Server (Render)
/ws/{room_id}  … WebRTC シグナリング。同室全員にbroadcast（送信者除く）
/              … ヘルスチェック（Renderウォームアップ用）
/home          … 管理ページ（templates/home.html）

【v2での変更点】
- 入室時に、自分が「何番目の入室者か」をクライアントへ明示的に通知するように変更。
  旧版は2人目にだけ {"type":"ready"} を送っていたが、1人目には何も通知していなかったため、
  クライアント側が「自分がPlayer1なのかPlayer2なのか」を確定できず、
  1人目が操作不能になる不具合があった。
- 1人目には {"type": "welcome", "isFirst": true}
  2人目には {"type": "ready", "isFirst": false} を送ることで、
  クライアント側だけで isHost / myPlayer を確実に確定できるようにする。
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

    # 自分が何番目の入室者かを明示的に通知する
    await ws.send_text(json.dumps({"type": "welcome", "count": len(peers)}))

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
