from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from glassbox.observability.trace_store import TraceStore, TraceEvent, get_default_store


app = FastAPI(title="GlassBox Trace Server", version="0.2.0")

store = get_default_store()
_active_ws: Set[WebSocket] = set()


def _broadcast_event(event: TraceEvent) -> None:
    payload = json.dumps({
        "id": event.id,
        "session_id": event.session_id,
        "ts": event.ts,
        "kind": event.kind,
        "payload": event.payload,
    })
    dead = set()
    for ws in list(_active_ws):
        try:
            asyncio.get_event_loop().call_soon_threadsafe(
                asyncio.ensure_future, ws.send_text(payload)
            )
        except Exception:
            dead.add(ws)
    _active_ws.difference_update(dead)


store.subscribe(_broadcast_event)


@app.get("/")
async def root() -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "service": "GlassBox Trace Server",
        "version": "0.2.0",
        "endpoints": {
            "sessions": "/api/sessions",
            "events": "/api/sessions/{session_id}/events",
            "tail": "/api/sessions/{session_id}/tail",
            "health": "/api/health",
            "websocket": "/ws/trace",
        }
    })


@app.get("/api/sessions")
async def list_sessions() -> JSONResponse:
    sessions = store.list_sessions()
    return JSONResponse(sessions)


@app.get("/api/sessions/{session_id}/events")
async def get_session_events(session_id: str, after: float = 0.0) -> JSONResponse:
    events = store.replay(session_id, after_ts=after)
    return JSONResponse(events)


@app.get("/api/sessions/{session_id}/tail")
async def tail_session(session_id: str, n: int = 50) -> JSONResponse:
    events = store.tail(session_id, n=n)
    return JSONResponse(events)


@app.websocket("/ws/trace")
async def websocket_trace(ws: WebSocket) -> None:
    await ws.accept()
    _active_ws.add(ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        _active_ws.discard(ws)
    except Exception:
        _active_ws.discard(ws)


@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "ts": time.time(), "version": "0.2.0"})


def run_trace_server(host: str = "127.0.0.1", port: int = 8001) -> None:
    import uvicorn
    print(f"GlassBox Trace Server running at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")
