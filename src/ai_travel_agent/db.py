"""SQLite storage for auth, trips and RAG chunks. One file, no external service."""

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .config import settings

_lock = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect():
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _lock, connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                phone TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                last_login TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS otp (
                phone TEXT PRIMARY KEY,
                code_hash TEXT NOT NULL,
                expires_at REAL NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                thread_id TEXT NOT NULL,
                brief TEXT NOT NULL,
                plan TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_trips_user ON trips(user_id, id DESC);
            CREATE TABLE IF NOT EXISTS rag_chunks (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding TEXT NOT NULL,
                model TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rag_source ON rag_chunks(source);
            """
        )


def upsert_user(phone: str) -> bool:
    now = utc_now()
    with _lock, connect() as conn:
        row = conn.execute("SELECT 1 FROM users WHERE phone=?", (phone,)).fetchone()
        if row:
            conn.execute("UPDATE users SET last_login=? WHERE phone=?", (now, phone))
            return False
        conn.execute(
            "INSERT INTO users(phone, created_at, last_login) VALUES (?, ?, ?)",
            (phone, now, now),
        )
        return True


def save_otp(phone: str, code_hash: str, expires_at: float, created_at: float) -> None:
    with _lock, connect() as conn:
        conn.execute(
            "INSERT INTO otp(phone, code_hash, expires_at, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(phone) DO UPDATE SET code_hash=excluded.code_hash, "
            "expires_at=excluded.expires_at, created_at=excluded.created_at",
            (phone, code_hash, expires_at, created_at),
        )


def get_otp(phone: str):
    with connect() as conn:
        return conn.execute("SELECT * FROM otp WHERE phone=?", (phone,)).fetchone()


def delete_otp(phone: str) -> None:
    with _lock, connect() as conn:
        conn.execute("DELETE FROM otp WHERE phone=?", (phone,))


def save_trip(user_id: str, thread_id: str, brief: dict, plan: str) -> None:
    with _lock, connect() as conn:
        conn.execute(
            "INSERT INTO trips(user_id, thread_id, brief, plan, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, thread_id, json.dumps(brief, ensure_ascii=False), plan, utc_now()),
        )


def recent_trips(user_id: str, limit: int = 3) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT brief, plan, created_at FROM trips WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [
        {"brief": json.loads(r["brief"]), "plan": r["plan"], "created_at": r["created_at"]}
        for r in rows
    ]
