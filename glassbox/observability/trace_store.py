from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, Iterator, List, Optional


EVENT_KINDS = (
    "thought",
    "action",
    "observation",
    "failure",
    "recovery",
    "tool_call",
    "score_update",
    "capture_stage",
    "repair_task",
    "session_start",
    "session_end",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    ts          REAL NOT NULL,
    kind        TEXT NOT NULL,
    payload     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id, ts);
CREATE INDEX IF NOT EXISTS idx_events_kind    ON events(kind, ts);

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    url         TEXT,
    started_at  REAL NOT NULL,
    ended_at    REAL,
    outcome     TEXT,
    scores      TEXT
);
"""


@dataclass
class TraceEvent:
    kind: str
    payload: Dict[str, Any]
    session_id: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    ts: float = field(default_factory=time.time)


class TraceStore:
    def __init__(self, db_path: str = "glassbox_trace.db") -> None:
        self.db_path = str(Path(db_path).resolve())
        self._local = threading.local()
        self._init_schema()
        self._subscribers: List[Any] = []

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    def start_session(
        self, session_id: str, url: Optional[str] = None
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO sessions (id, url, started_at) VALUES (?, ?, ?)",
                (session_id, url or "", time.time()),
            )
        self.append(TraceEvent(
            kind="session_start",
            session_id=session_id,
            payload={"url": url, "session_id": session_id},
        ))

    def end_session(
        self, session_id: str, outcome: str, scores: Optional[Dict] = None
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE sessions SET ended_at=?, outcome=?, scores=? WHERE id=?",
                (time.time(), outcome, json.dumps(scores or {}), session_id),
            )
        self.append(TraceEvent(
            kind="session_end",
            session_id=session_id,
            payload={"outcome": outcome, "scores": scores or {}},
        ))

    def append(self, event: TraceEvent) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO events (id, session_id, ts, kind, payload) VALUES (?, ?, ?, ?, ?)",
                (
                    event.id,
                    event.session_id,
                    event.ts,
                    event.kind,
                    json.dumps(event.payload),
                ),
            )
        for sub in list(self._subscribers):
            try:
                sub(event)
            except Exception:
                pass

    def subscribe(self, callback: Any) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Any) -> None:
        self._subscribers = [s for s in self._subscribers if s != callback]

    def replay(
        self, session_id: str, after_ts: float = 0.0
    ) -> List[Dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT * FROM events WHERE session_id=? AND ts>? ORDER BY ts ASC",
            (session_id, after_ts),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "ts": row["ts"],
                "kind": row["kind"],
                "payload": json.loads(row["payload"]),
            }
            for row in rows
        ]

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [
            {
                "id": row["id"],
                "url": row["url"],
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "outcome": row["outcome"],
                "scores": json.loads(row["scores"]) if row["scores"] else {},
            }
            for row in rows
        ]

    def tail(self, session_id: str, n: int = 50) -> List[Dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT * FROM events WHERE session_id=? ORDER BY ts DESC LIMIT ?",
            (session_id, n),
        ).fetchall()
        result = [
            {
                "id": row["id"],
                "ts": row["ts"],
                "kind": row["kind"],
                "payload": json.loads(row["payload"]),
            }
            for row in rows
        ]
        return list(reversed(result))


_default_store: Optional[TraceStore] = None


def get_default_store() -> TraceStore:
    global _default_store
    if _default_store is None:
        _default_store = TraceStore()
    return _default_store
