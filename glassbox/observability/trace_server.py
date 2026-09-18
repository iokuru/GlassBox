from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from glassbox.observability.trace_store import TraceStore, TraceEvent, get_default_store


app = FastAPI(title="GlassBox Trace Server", version="0.2.0")

static_dir = Path(__file__).parent / "static_trace"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

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


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    static_index = static_dir / "index.html"
    if static_index.exists():
        return HTMLResponse(content=static_index.read_text(encoding="utf-8"))
    return HTMLResponse(content=INLINE_DASHBOARD)


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


INLINE_DASHBOARD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GlassBox Trace</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0d0e11; color: #e8e6df; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
  header { padding: 12px 20px; background: #141517; border-bottom: 1px solid #252830; display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 15px; letter-spacing: 0.1em; color: #a0f0a0; font-weight: 500; }
  #dot { width: 8px; height: 8px; border-radius: 50%; background: #555; }
  #dot.live { background: #4ade80; box-shadow: 0 0 6px #4ade80; }
  .grid { display: grid; grid-template-columns: 220px 1fr 320px; height: calc(100vh - 45px); }
  .pane { overflow-y: auto; border-right: 1px solid #1e2028; }
  .pane:last-child { border-right: none; }
  .pane-head { padding: 8px 12px; font-size: 11px; color: #666; border-bottom: 1px solid #1e2028; letter-spacing: 0.08em; }
  .session-item { padding: 8px 12px; cursor: pointer; border-bottom: 1px solid #1a1c22; }
  .session-item:hover { background: #1a1c22; }
  .session-item.active { background: #1e2a1e; border-left: 3px solid #4ade80; }
  .session-url { color: #8b9bc4; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .session-id { color: #555; font-size: 10px; }
  #feed { padding: 10px; }
  .event { padding: 5px 8px; margin-bottom: 3px; border-radius: 3px; border-left: 3px solid #333; background: #111215; }
  .event.thought { border-color: #6366f1; }
  .event.action { border-color: #f59e0b; }
  .event.failure { border-color: #ef4444; }
  .event.recovery { border-color: #10b981; }
  .event.score_update { border-color: #3b82f6; }
  .event.capture_stage { border-color: #8b5cf6; }
  .event-kind { font-size: 10px; color: #555; text-transform: uppercase; letter-spacing: 0.06em; }
  .event-content { color: #ccc; margin-top: 2px; }
  #scores-pane { padding: 12px; }
  .score-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #1a1c22; }
  .score-label { color: #666; }
  .score-value { font-weight: 600; }
  .score-value.good { color: #4ade80; }
  .score-value.warn { color: #f59e0b; }
  .score-value.bad { color: #ef4444; }
</style>
</head>
<body>
<header>
  <div id="dot"></div>
  <h1>GLASSBOX TRACE</h1>
  <span id="conn-status" style="color:#555;font-size:11px">connecting...</span>
</header>
<div class="grid">
  <div class="pane" id="sessions-pane">
    <div class="pane-head">SESSIONS</div>
    <div id="sessions-list"></div>
  </div>
  <div class="pane" id="feed-pane">
    <div class="pane-head">EVENT STREAM</div>
    <div id="feed"></div>
  </div>
  <div class="pane" id="scores-pane">
    <div class="pane-head">LIVE SCORES</div>
    <div id="scores"></div>
  </div>
</div>
<script>
  const dot = document.getElementById('dot');
  const feed = document.getElementById('feed');
  const scoreDiv = document.getElementById('scores');
  let scores = {};

  function loadSessions() {
    fetch('/api/sessions').then(r => r.json()).then(sessions => {
      const list = document.getElementById('sessions-list');
      list.innerHTML = '';
      for (const s of sessions) {
        const el = document.createElement('div');
        el.className = 'session-item';
        el.innerHTML = `<div class="session-url">${s.url || '—'}</div>
          <div class="session-id">${s.id}</div>
          <div style="color:#555;font-size:10px">${s.outcome || 'running'}</div>`;
        el.onclick = () => loadSession(s.id, el);
        list.appendChild(el);
      }
    });
  }

  function loadSession(id, el) {
    document.querySelectorAll('.session-item').forEach(e => e.classList.remove('active'));
    if (el) el.classList.add('active');
    fetch('/api/sessions/' + id + '/tail?n=80').then(r => r.json()).then(evts => {
      feed.innerHTML = '';
      evts.forEach(addEvent);
    });
  }

  function addEvent(ev) {
    const el = document.createElement('div');
    el.className = 'event ' + (ev.kind || '');
    const content = ev.payload?.content || ev.payload?.message || ev.payload?.stage || JSON.stringify(ev.payload).slice(0, 120);
    el.innerHTML = `<div class="event-kind">${ev.kind}</div><div class="event-content">${content}</div>`;
    feed.insertBefore(el, feed.firstChild);
    if (feed.children.length > 200) feed.removeChild(feed.lastChild);
  }

  function updateScores(payload) {
    Object.assign(scores, payload);
    scoreDiv.innerHTML = '';
    const rows = [
      ['SSIM', scores.ssim, 0.75],
      ['Palette ΔE', scores.palette_de, null],
      ['Layout IoU', scores.layout_iou, 0.5],
      ['Motion', scores.motion, 0.6],
      ['Overall', scores.overall, 0.7],
    ];
    for (const [label, val, threshold] of rows) {
      if (val === undefined) continue;
      const cls = threshold === null
        ? (val < 10 ? 'good' : val < 20 ? 'warn' : 'bad')
        : (val >= threshold ? 'good' : val >= threshold * 0.7 ? 'warn' : 'bad');
      const display = label === 'Palette ΔE' ? val.toFixed(1) + ' ΔE' : (val * 100).toFixed(1) + '%';
      scoreDiv.innerHTML += `<div class="score-row"><span class="score-label">${label}</span><span class="score-value ${cls}">${display}</span></div>`;
    }
  }

  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws/trace`);
  ws.onopen = () => {
    dot.classList.add('live');
    document.getElementById('conn-status').textContent = 'live';
    setInterval(() => ws.send('ping'), 15000);
  };
  ws.onclose = () => {
    dot.classList.remove('live');
    document.getElementById('conn-status').textContent = 'disconnected';
  };
  ws.onmessage = (msg) => {
    const ev = JSON.parse(msg.data);
    if (!ev.kind) return;
    addEvent(ev);
    if (ev.kind === 'score_update') updateScores(ev.payload);
  };

  loadSessions();
  setInterval(loadSessions, 10000);
</script>
</body>
</html>"""


def run_trace_server(host: str = "127.0.0.1", port: int = 8001) -> None:
    import uvicorn
    print(f"GlassBox Trace Server running at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")
