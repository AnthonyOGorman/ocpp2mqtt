# -*- coding: utf-8 -*-

import asyncio
import json
import logging
from dataclasses import asdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import uvicorn

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os


logger = logging.getLogger("webui")

app = FastAPI()

BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
WEBUI_PORT = int(os.getenv("WEBUI_PORT", "8080"))

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# These will be injected from ocpp_relay_server.py
relay = None
snoop_queue = None


# ---------- Models ----------

class InjectRequest(BaseModel):
    cp_id: str
    direction: str   # "cp" or "csms"
    payload: str     # raw JSON string


# ---------- WebSocket: live snoop stream ----------

@app.websocket("/ws/snoop")
async def ws_snoop(ws: WebSocket):
    await ws.accept()
    logger.info("Web UI client connected to snoop stream")

    try:
        while True:
            msg = await snoop_queue.get()
            await ws.send_text(json.dumps(asdict(msg)))
    except WebSocketDisconnect:
        logger.info("Web UI client disconnected from snoop stream")


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/api/cps")
def list_connected_cps():
    return {
        "cps": list(relay.cp_connections.keys())
    }

# ---------- HTTP: injection ----------

@app.post("/api/inject")
async def inject(req: InjectRequest):
    try:
        if req.direction == "to_cp":
            await relay.inject_to_cp(req.cp_id, req.payload)
        elif req.direction == "to_csms":
            await relay.inject_to_csms(req.payload)
        else:
            raise HTTPException(status_code=400, detail="Invalid direction")

        return {"status": "ok"}

    except ValueError as e:
        # No CP connected, or bad CP ID
        raise HTTPException(status_code=409, detail=str(e))


# ---------- Startup helper ----------

def start_webui(relay_instance, snoop_q, host="0.0.0.0", port=WEBUI_PORT):
    global relay, snoop_queue
    relay = relay_instance
    snoop_queue = snoop_q

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        loop="asyncio"
    )
    server = uvicorn.Server(config)
    return server
