"""
TRINKER - Build Order Manager
CRUD operations for build orders in the SQLite database.
Acts as the single access point for persisting and retrieving BuildOrder objects.
"""

import json
from typing import Optional

from ..core.config import BO_DIR
from ..core.database import db_conn, json_dumps, json_loads, now_iso
from ..core.logger import logger
from .models import BuildOrder, BuildStep

# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def get_all_build_orders(
    *,
    civ: Optional[str] = None,
    tag: Optional[str] = None,
    favorites_only: bool = False,
    search: Optional[str] = None,
) -> list[BuildOrder]:
    """
    Return all build orders, with optional filters.

    Args:
        civ:            Filter by civilization name (exact match, case-insensitive).
        tag:            Filter by tag (substring match inside JSON array).
        favorites_only: If True, return only starred builds.
        search:         Full-text search across name, civ, and strategy.

    Returns:
        List of BuildOrder objects, newest first.
    """
    conditions = []
    params: list = []

    if civ:
        conditions.append("(LOWER(civ) = ? OR civ = 'Any')")
        params.append(civ.lower())
    if tag:
        conditions.append("LOWER(tags) LIKE ?")
        params.append(f"%{tag.lower()}%")
    if favorites_only:
        conditions.append("is_favorite = 1")
    if search:
        q = f"%{search.lower()}%"
        conditions.append("(LOWER(name) LIKE ? OR LOWER(civ) LIKE ? OR LOWER(strategy) LIKE ?)")
        params.extend([q, q, q])

    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"SELECT * FROM build_orders {where_sql} ORDER BY updated_at DESC"

    with db_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [_row_to_build_order(dict(row)) for row in rows]


def get_build_order(bo_id: int) -> Optional[BuildOrder]:
    """Fetch a single build order by primary key. Returns None if not found."""
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM build_orders WHERE id = ?", (bo_id,)).fetchone()
    if row is None:
        return None
    return _row_to_build_order(dict(row))


def get_build_order_by_external_id(external_id: str) -> Optional[BuildOrder]:
    """Find a cached build order by external source ID (e.g. buildorderguide slug)."""
    with db_conn() as conn:
        row = conn.execute(
            "SELECT * FROM build_orders WHERE external_id = ?", (external_id,)
        ).fetchone()
    return _row_to_build_order(dict(row)) if row else None


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def save_build_order(bo: BuildOrder) -> BuildOrder:
    """
    Insert or update a build order.
    If bo.id is set, performs an UPDATE; otherwise inserts and sets bo.id.

    Returns:
        The same BuildOrder with id and timestamps populated.
    """
    ts = now_iso()
    steps_json = json_dumps([s.to_dict() for s in bo.steps])
    tags_json = json_dumps(bo.tags)

    with db_conn() as conn:
        if bo.id is None:
            bo.created_at = ts
            bo.updated_at = ts
            cur = conn.execute(
                """INSERT INTO build_orders
                   (external_id, name, civ, strategy, difficulty, tags, author,
                    source_url, steps_json, notes, is_favorite, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    bo.external_id,
                    bo.name,
                    bo.civ,
                    bo.strategy,
                    bo.difficulty,
                    tags_json,
                    bo.author,
                    bo.source_url,
                    steps_json,
                    bo.notes,
                    int(bo.is_favorite),
                    bo.created_at,
                    bo.updated_at,
                ),
            )
            bo.id = cur.lastrowid
            logger.info("Inserted build order id=%d '%s'", bo.id, bo.name)
        else:
            bo.updated_at = ts
            conn.execute(
                """UPDATE build_orders SET
                   external_id=?, name=?, civ=?, strategy=?, difficulty=?, tags=?,
                   author=?, source_url=?, steps_json=?, notes=?, is_favorite=?, updated_at=?
                   WHERE id=?""",
                (
                    bo.external_id,
                    bo.name,
                    bo.civ,
                    bo.strategy,
                    bo.difficulty,
                    tags_json,
                    bo.author,
                    bo.source_url,
                    steps_json,
                    bo.notes,
                    int(bo.is_favorite),
                    bo.updated_at,
                    bo.id,
                ),
            )
            logger.info("Updated build order id=%d '%s'", bo.id, bo.name)
    return bo


def delete_build_order(bo_id: int) -> bool:
    """Delete a build order by id. Returns True if a row was deleted."""
    with db_conn() as conn:
        cur = conn.execute("DELETE FROM build_orders WHERE id = ?", (bo_id,))
    deleted = cur.rowcount > 0
    if deleted:
        logger.info("Deleted build order id=%d", bo_id)
    return deleted


def toggle_favorite(bo_id: int) -> bool:
    """Toggle the is_favorite flag. Returns the new state (True = favorited)."""
    with db_conn() as conn:
        row = conn.execute("SELECT is_favorite FROM build_orders WHERE id = ?", (bo_id,)).fetchone()
        if row is None:
            return False
        new_val = 0 if row["is_favorite"] else 1
        conn.execute(
            "UPDATE build_orders SET is_favorite=?, updated_at=? WHERE id=?",
            (new_val, now_iso(), bo_id),
        )
    return bool(new_val)


# ---------------------------------------------------------------------------
# Import / Export helpers
# ---------------------------------------------------------------------------


def import_and_save(bo: BuildOrder) -> BuildOrder:
    """
    Check if a build order with the same external_id already exists.
    If yes, update it; if no, insert it fresh.
    """
    if bo.external_id:
        existing = get_build_order_by_external_id(bo.external_id)
        if existing:
            bo.id = existing.id
            bo.created_at = existing.created_at
    return save_build_order(bo)


def export_all_to_json(path=None) -> str:
    """
    Serialize all build orders to JSON.
    Writes to path (or auto-generates a filename in EXPORT_DIR).
    Returns the path written.
    """
    from pathlib import Path as _P

    bos = get_all_build_orders()
    data = [bo.to_dict() for bo in bos]
    out = _P(path) if path else (BO_DIR / f"export_{now_iso()[:10]}.json")
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Exported %d build orders to %s", len(bos), out)
    return str(out)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _row_to_build_order(row: dict) -> BuildOrder:
    """Convert a raw DB row dict to a BuildOrder with nested BuildStep list."""
    steps_raw = json_loads(row.get("steps_json", "[]"))
    tags = json_loads(row.get("tags", "[]"))
    steps = [BuildStep.from_dict(s) for s in steps_raw]
    return BuildOrder(
        id=row["id"],
        external_id=row.get("external_id"),
        name=row["name"],
        civ=row.get("civ", "Any"),
        strategy=row.get("strategy", ""),
        difficulty=row.get("difficulty", "Medium"),
        tags=tags,
        author=row.get("author", ""),
        source_url=row.get("source_url", ""),
        steps=steps,
        notes=row.get("notes", ""),
        is_favorite=bool(row.get("is_favorite", 0)),
        created_at=row.get("created_at", ""),
        updated_at=row.get("updated_at", ""),
    )
