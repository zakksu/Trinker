#!/usr/bin/env python3
"""
Sync full buildorderguide.com catalog into TRINKER SQLite.

Discovers builds via Firebase Firestore (card/modal site), rate-limits fetches,
caches JSON, imports + enriches steps.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.build_orders.bog_firestore import (  # noqa: E402
    build_order_from_bog_data,
    cache_build_json,
    discover_build_urls as firestore_discover_urls,
    fetch_published_build,
)
from src.build_orders.manager import get_all_build_orders, import_and_save  # noqa: E402
from src.build_orders.step_enricher import enrich_steps  # noqa: E402
from src.core.config import BUILDORDERGUIDE_BASE  # noqa: E402
from src.core.database import db_conn, init_db  # noqa: E402
from src.core.logger import logger  # noqa: E402
from src.core.resource_profile import get_resource_profile  # noqa: E402

CACHE_DIR = ROOT / "data" / "buildorderguide_cache"
PROGRESS_PATH = CACHE_DIR / "progress.json"
RATE_LIMIT_SEC = 1.0
MIN_BUILDS_TARGET = 50
BUILD_URL_RE = re.compile(
    r"https?://(?:www\.)?buildorderguide\.com/builds/([A-Za-z0-9_-]+)",
    re.I,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _manifest_path() -> Path:
    return CACHE_DIR / "manifest.json"


def _load_manifest() -> dict:
    path = _manifest_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"urls": [], "synced_at": "", "version": 2}


def _save_manifest(urls: list[str]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _manifest_path().write_text(
        json.dumps(
            {"urls": sorted(set(urls)), "synced_at": _now_iso(), "version": 2},
            indent=2,
        ),
        encoding="utf-8",
    )


def _load_progress() -> dict:
    if PROGRESS_PATH.exists():
        try:
            return json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"done": [], "failed": {}, "last_url": ""}


def _save_progress(progress: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PROGRESS_PATH.write_text(json.dumps(progress, indent=2), encoding="utf-8")


def _slug_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) >= 2 and parts[0] == "builds":
        return parts[1]
    raise ValueError(f"Invalid build URL: {url}")


def _load_cached_build(slug: str) -> dict | None:
    path = CACHE_DIR / f"{slug}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def discover_build_urls(
    *,
    fetcher: Callable[[str], requests.Response] | None = None,
    max_pages: int = 20,
) -> list[str]:
    """Discover build URLs from Firestore published-builds collection."""
    del fetcher, max_pages  # legacy params kept for tests
    try:
        urls = firestore_discover_urls()
    except Exception as exc:
        logger.warning("Firestore discovery failed: %s", exc)
        urls = []

    _save_manifest(urls)
    logger.info("Discovered %d buildorderguide URLs", len(urls))
    return urls


def import_build_url(
    url: str,
    *,
    fetcher: Callable[[str], requests.Response] | None = None,
    enrich: bool = True,
) -> bool:
    """Fetch from Firestore, parse, enrich, and upsert one build order."""
    del fetcher
    slug = _slug_from_url(url)
    cached = _load_cached_build(slug)

    try:
        if cached:
            bo = build_order_from_bog_data(cached)
        else:
            data = fetch_published_build(slug)
            cache_build_json(slug, data, CACHE_DIR)
            bo = build_order_from_bog_data(data)
    except Exception as exc:
        raise RuntimeError(f"Firestore import failed for {slug}: {exc}") from exc

    if enrich and bo.steps:
        before = len(bo.steps)
        bo.steps = enrich_steps(bo.steps)
        logger.debug("Enriched %s: %d -> %d steps", slug, before, len(bo.steps))

    import_and_save(bo)
    return True


def sync_all(
    *,
    urls: list[str] | None = None,
    force: bool = False,
    max_builds: int | None = None,
    fetcher: Callable[[str], requests.Response] | None = None,
) -> dict:
    """Sync discovered builds with resume support."""
    del fetcher
    init_db()
    if urls is None:
        manifest = _load_manifest()
        urls = manifest.get("urls") or []
        if not urls or force:
            urls = discover_build_urls()

    progress = _load_progress()
    done = set(progress.get("done") or [])
    failed: dict[str, str] = dict(progress.get("failed") or {})

    if force:
        done.clear()
        failed.clear()

    pending = [u for u in urls if u not in done]
    if max_builds is not None:
        pending = pending[:max_builds]

    imported = 0
    errors = 0
    for i, url in enumerate(pending, start=1):
        slug = _slug_from_url(url)
        try:
            import_build_url(url, enrich=True)
            done.add(url)
            failed.pop(url, None)
            imported += 1
            logger.info("[%d/%d] Synced %s", i, len(pending), url)
        except Exception as exc:
            failed[url] = str(exc)[:200]
            errors += 1
            logger.warning("Failed %s: %s", url, exc)
        progress = {"done": sorted(done), "failed": failed, "last_url": url}
        _save_progress(progress)
        time.sleep(RATE_LIMIT_SEC)

    total = len(get_all_build_orders())
    result = {
        "imported": imported,
        "errors": errors,
        "total_builds": total,
        "pending": len(pending),
        "urls_discovered": len(urls),
    }
    logger.info(
        "Sync complete: discovered=%d imported=%d errors=%d total_in_db=%d",
        len(urls),
        imported,
        errors,
        total,
    )
    return result


def needs_sync(*, min_builds: int = MIN_BUILDS_TARGET) -> bool:
    """True when DB has fewer than min_builds or manifest is empty."""
    try:
        with db_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM build_orders").fetchone()[0]
    except Exception:
        return True
    if count < min_builds:
        return True
    manifest = _load_manifest()
    return not manifest.get("urls")


def maybe_background_sync(*, min_builds: int = MIN_BUILDS_TARGET) -> None:
    """Spawn a daemon thread for first-launch sync when library is thin."""
    if not needs_sync(min_builds=min_builds):
        return

    import threading

    def _run() -> None:
        try:
            logger.info("Background buildorderguide sync starting…")
            sync_all(max_builds=None)
        except Exception as exc:
            logger.warning("Background buildorderguide sync failed: %s", exc)

    threading.Thread(target=_run, daemon=True, name="bog-sync").start()


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync buildorderguide.com into TRINKER")
    parser.add_argument("--force", action="store_true", help="Re-discover and re-import all")
    parser.add_argument("--discover-only", action="store_true", help="Only discover URLs")
    parser.add_argument("--if-stale", action="store_true", help="Skip if DB already has enough builds")
    parser.add_argument("--max", type=int, default=None, help="Max builds to import this run")
    parser.add_argument("--min-builds", type=int, default=MIN_BUILDS_TARGET)
    args = parser.parse_args()

    logger.info("Resource profile: %s", get_resource_profile())

    if args.if_stale and not needs_sync(min_builds=args.min_builds):
        print(f"Build library OK (>= {args.min_builds} builds). Skipping sync.")
        return 0

    if args.discover_only:
        urls = discover_build_urls()
        print(f"Discovered {len(urls)} URLs -> {_manifest_path()}")
        return 0

    result = sync_all(force=args.force, max_builds=args.max)
    print(json.dumps(result, indent=2))
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
