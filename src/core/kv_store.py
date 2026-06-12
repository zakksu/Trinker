"""
TRINKER - SQLite key-value store helpers (supplements settings.json).
"""

from __future__ import annotations

import json
from typing import Any, Optional

from .database import db_conn


def kv_get(key: str, default: Optional[str] = None) -> Optional[str]:
    with db_conn() as conn:
        row = conn.execute("SELECT value FROM kv_store WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return row["value"]


def kv_set(key: str, value: str) -> None:
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO kv_store (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def kv_get_json(key: str, default: Any = None) -> Any:
    raw = kv_get(key)
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def kv_set_json(key: str, value: Any) -> None:
    kv_set(key, json.dumps(value))
