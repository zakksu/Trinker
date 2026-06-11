"""
TRINKER 2.0 - Purge messy sessions and re-import multiplayer replays.
Run once after upgrading: python scripts/rebuild_data.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.analytics.session import purge_low_quality_sessions
from src.core.database import init_db
from src.replay.bulk_import import import_all_replays
from src.replay.parser import find_replay_files


def main() -> int:
    init_db()
    mp = [p for p in find_replay_files() if p.name.startswith("MP Replay")]
    print(f"Found {len(mp)} multiplayer replay(s).")

    deleted = purge_low_quality_sessions()
    print(f"Purged {deleted} low-quality session(s).")

    result = import_all_replays(mp_only=True, skip_existing=True)
    print(f"Imported: {result.imported} | Skipped: {result.skipped} | Failed: {result.failed}")
    for line in result.details:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
