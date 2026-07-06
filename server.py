"""
Signaling Server (Render)
/ws/p2p/{room_id}  … WebRTC シグナリング。P2P
/ws/mesh/{room_id}  … WebRTC シグナリング。同室全員にbroadcast（送信者除く）
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
meshRooms: dict[str, list[WebSocket]] = {}
p2pRooms: dict[str, list[WebSocket]] = {}

@app.websocket("/ws/p2p/{room_id}")
async def signaling_p2p(ws: WebSocket, room_id: str):
    await ws.accept()
    
    # 満員チェック（すでに2人いる場合は接続を拒否して切断する）
    if room_id in p2pRooms and len(p2pRooms[room_id]) >= 2:
        await ws.send_text(json.dumps({"type": "error", "message": "Room is full"}))
        await ws.close()
        return

    p2pRooms.setdefault(room_id, []).append(ws)

    # 人数に応じた役割分担の通知
    await ws.send_text(json.dumps({"type": "welcome", "count": len(p2pRooms[room_id])}))

    try:
        while True:
            data = await ws.receive_text()
            for peer in p2pRooms[room_id]:
                if peer is not ws:
                    await peer.send_text(data)
    except WebSocketDisconnect:
        if room_id in p2pRooms:
            if ws in p2pRooms[room_id]:
                p2pRooms[room_id].remove(ws)
            if not p2pRooms[room_id]:
                del p2pRooms[room_id]


@app.websocket("/ws/mesh/{room_id}")
async def signaling_mesh(ws: WebSocket, room_id: str):
    await ws.accept()
    meshRooms.setdefault(room_id, []).append(ws)

    # 自分が何番目の入室者かを明示的に通知する
    await ws.send_text(json.dumps({"type": "welcome", "list": list(meshRooms[room_id].keys())}))

    try:
        while True:
            data = await ws.receive_text()
            for peer in meshRooms[room_id]:
                if peer is not ws:
                    await peer.send_text(data)
    except WebSocketDisconnect:
        if room_id in meshRooms:
            if ws in meshRooms[room_id]:
                meshRooms[room_id].remove(ws)
            if not meshRooms[room_id]:
                del meshRooms[room_id]


@app.get("/")
def health():
    """Renderウォームアップ・死活監視用。"""
    # 存在する全部屋の合計数を返すように修正
    total_rooms = len(meshRooms) + len(p2pRooms)
    return {"status": "ok", "rooms": total_rooms}


@app.get("/home")
def home(request: Request):
    """管理ページ。"""
    mesh_keys = ",".join(list(meshRooms.keys()))
    p2p_keys = ",".join(list(p2pRooms.keys())) # join のタイポを修正
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"rooms": f"Mesh: [{mesh_keys}] | P2P: [{p2p_keys}]"},
    )
