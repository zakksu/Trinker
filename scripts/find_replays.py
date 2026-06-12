#!/usr/bin/env python3
"""Find and register AoE2 DE replay folders for TRINKER."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.replay_paths import ensure_replay_folders  # noqa: E402


def main() -> int:
    print()
    print("  TRINKER — Find AoE2 Replay Folders")
    print("  =================================")
    print()
    report = ensure_replay_folders(save=True)
    print(f"  Folders registered: {len(report.search_roots)}")
    for p in report.search_roots:
        print(f"    • {p}")
    print()
    if report.readable:
        print(f"  OK — {report.replay_count} replay(s) found.")
        print(f"  Newest: {report.newest_replay}")
    else:
        print("  No replays yet — play a game, then run this again.")
        for msg in report.messages:
            print(f"  → {msg}")
    print()
    return 0 if report.readable else 1


if __name__ == "__main__":
    raise SystemExit(main())
