#!/usr/bin/env python3
"""
Replay corpus regression runner.

Generates synthetic replays from manifest.json, runs parser + coach assertions,
and optionally downloads remote corpus entries when URLs are listed.

Usage:
    python scripts/replay_corpus_test.py
    python scripts/replay_corpus_test.py --download   # fetch remote entries (if any)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CORPUS_DIR = ROOT / "tests" / "fixtures" / "replays"


def main() -> int:
    parser = argparse.ArgumentParser(description="TRINKER replay corpus regression")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download remote replays listed in manifest.json",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=CORPUS_DIR,
        help="Path to corpus folder containing manifest.json",
    )
    args = parser.parse_args()

    from tests.fixtures.corpus_runner import ensure_corpus_files, ensure_remote_files, load_manifest, run_corpus_assertions

    manifest = load_manifest(args.corpus_dir)
    if args.download and manifest.get("remote"):
        ensure_remote_files(args.corpus_dir)

    ensure_corpus_files(args.corpus_dir)
    results = run_corpus_assertions(args.corpus_dir)

    ok = 0
    for r in results:
        status = "PASS" if r.ok else "FAIL"
        print(f"[{status}] {r.replay_id} — {r.detail} ({r.path.name})")
        if r.ok:
            ok += 1

    print(f"\n{ok}/{len(results)} corpus checks passed.")
    return 0 if ok == len(results) and results else 1


if __name__ == "__main__":
    sys.exit(main())
