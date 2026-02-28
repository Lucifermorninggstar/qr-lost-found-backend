from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from app.config import settings
from app.connectors import mongo, minio
from app.routers import auth, items, scan, lost, violation, history, dashboard, notifications, profile, scan_detail
from typing import Dict, List
import json

from fastapi.middleware.cors import CORSMiddleware


# ── Lifespan (startup + shutdown) ────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    mongo.connect()
    minio.connect()
    yield
    # Shutdown
    mongo.disconnect()
    minio.disconnect()


app = FastAPI(
    title      = settings.APP_NAME,
    docs_url   = "/docs",
    redoc_url  = "/redoc",
    openapi_url= "/openapi.json",
    lifespan   = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "ws://localhost:5173",
        "ws://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(items.router)
app.include_router(scan.router)
app.include_router(lost.router)
app.include_router(violation.router)
app.include_router(history.router)
app.include_router(dashboard.router)
app.include_router(notifications.router)
app.include_router(profile.router)
app.include_router(scan_detail.router)

# ── Root ─────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "app":    settings.APP_NAME,
        "env":    settings.ENV,
        "status": "running",
        "mongo":  mongo.ping(),
        "minio":  minio.ping(),
    }

@app.get("/health")
def health():
    return {
        "mongo": "ok" if mongo.ping() else "error",
        "minio": "ok" if minio.ping() else "error",
    }

# ── WebSocket ─────────────────────────────────────────────────
active_connections: Dict[str, List[WebSocket]] = {}

async def send_to_user(user_id: str, payload: dict):
    sockets = active_connections.get(str(user_id), [])
    dead = []
    for ws in sockets:
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            dead.append(ws)
    for ws in dead:
        sockets.remove(ws)

@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    await websocket.accept()
    user_id = websocket.query_params.get("user_id")
    if not user_id:
        await websocket.send_text('{"error": "user_id required"}')
        await websocket.close(code=1008)
        return
    uid = str(user_id)
    active_connections.setdefault(uid, []).append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_connections.get(uid, []):
            active_connections[uid].remove(websocket)
        if not active_connections.get(uid):
            active_connections.pop(uid, None)