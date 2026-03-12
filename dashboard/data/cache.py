"""SQLite cache layer to avoid redundant API calls."""

import json
import sqlite3
import time
from contextlib import contextmanager

from dashboard.config import CACHE_TTL, DB_PATH


def _init_db(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            timestamp REAL NOT NULL
        )
        """
    )
    conn.commit()


@contextmanager
def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        _init_db(conn)
        yield conn
    finally:
        conn.close()


def get(key: str, ttl: int | None = None) -> dict | list | None:
    """Retrieve a cached value if it exists and hasn't expired."""
    ttl = ttl if ttl is not None else CACHE_TTL
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT value, timestamp FROM cache WHERE key = ?", (key,)
        ).fetchone()
    if row is None:
        return None
    value, ts = row
    if time.time() - ts > ttl:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def put(key: str, value) -> None:
    """Store a value in the cache."""
    serialized = json.dumps(value, default=str)
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, timestamp) VALUES (?, ?, ?)",
            (key, serialized, time.time()),
        )
        conn.commit()


def invalidate(key: str) -> None:
    """Remove a specific key from the cache."""
    with _get_conn() as conn:
        conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        conn.commit()


def clear() -> None:
    """Clear all cached data."""
    with _get_conn() as conn:
        conn.execute("DELETE FROM cache")
        conn.commit()
