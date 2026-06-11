"""Import all AoE2 replays into TRINKER sessions. Run: python scripts/import_replays.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.database import init_db
from src.replay.bulk_import import import_all_replays
from src.replay.parser import find_replay_files


def main() -> int:
    init_db()
    found = find_replay_files()
    print(f"Found {len(found)} replay file(s) in AoE2 folders.")
    result = import_all_replays(mp_only=False)
    print(f"\nImported: {result.imported}  |  Skipped: {result.skipped}  |  Failed: {result.failed}")
    for line in result.details:
        print(f"  {line}")
    return 0 if result.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
