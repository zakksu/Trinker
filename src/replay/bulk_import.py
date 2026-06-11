"""
TRINKER 2.0 - Bulk Replay Import
Imports multiplayer replays as validated practice sessions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..analytics.session import save_session
from ..build_orders.manager import get_build_order
from ..core.database import db_conn
from ..core.logger import logger
from .parser import find_replay_files
from .profile import extract_replay_profile
from .session_builder import profile_to_session


@dataclass
class BulkImportResult:
    imported: int = 0
    skipped: int = 0
    failed: int = 0
    details: list[str] = field(default_factory=list)


def _existing_replay_paths() -> set[str]:
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT replay_path FROM sessions WHERE replay_path IS NOT NULL AND replay_path != ''"
        ).fetchall()
    return {r["replay_path"] for r in rows}


def import_all_replays(
    *,
    limit: Optional[int] = None,
    preferred_bo_id: Optional[int] = None,
    skip_existing: bool = True,
    mp_only: bool = True,
    days_back: Optional[int] = None,
) -> BulkImportResult:
    """Import .aoe2record files as validated practice sessions."""
    result = BulkImportResult()
    existing = _existing_replay_paths() if skip_existing else set()
    replays = find_replay_files()
    cutoff = None
    if days_back is not None:
        cutoff = datetime.now(timezone.utc).timestamp() - days_back * 86400

    for path in replays:
        if mp_only and not path.name.startswith("MP Replay"):
            continue
        if cutoff is not None:
            try:
                if path.stat().st_mtime < cutoff:
                    continue
            except OSError:
                continue
        if limit is not None and result.imported >= limit:
            break

        resolved = str(path.resolve())
        if resolved in existing:
            result.skipped += 1
            result.details.append(f"SKIP: {path.name}")
            continue

        try:
            profile = extract_replay_profile(path)
            session = profile_to_session(profile, path, preferred_bo_id=preferred_bo_id)
            if not session:
                result.failed += 1
                result.details.append(f"FAIL (no civ match): {path.name} civ={profile.civ}")
                continue

            save_session(session)
            result.imported += 1
            bo = get_build_order(session.build_order_id)
            bo_name = bo.name if bo else f"BO#{session.build_order_id}"
            result.details.append(
                f"OK: {path.name} -> {bo_name} [{profile.data_quality}] "
                f"feudal={session.feudal_time_sec} civ={profile.civ}"
            )
            existing.add(resolved)
        except Exception as exc:
            result.failed += 1
            result.details.append(f"FAIL: {path.name} - {exc}")
            logger.warning("Bulk import failed for %s: %s", path, exc)

    logger.info(
        "Bulk import: %d imported, %d skipped, %d failed",
        result.imported, result.skipped, result.failed,
    )
    return result
