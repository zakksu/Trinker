#!/usr/bin/env python3
"""
TRINKER agent ship — test, commit, push, release (autonomous).

Used when the user has delegated git/release to the Cursor agent.
Skips release confirmation popup (--yes).

Usage:
    python scripts/agent_ship.py "Add feature X"
    python scripts/agent_ship.py "Fix bug Y" --no-release
    python scripts/agent_ship.py --release-only
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=ROOT, check=check)


def _git_has_changes() -> bool:
    r = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return bool(r.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent autonomous ship pipeline")
    parser.add_argument("message", nargs="?", default="", help="Commit message")
    parser.add_argument("--no-release", action="store_true", help="Commit+push only")
    parser.add_argument("--release-only", action="store_true", help="Skip commit; release only")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest")
    parser.add_argument("--no-push", action="store_true", help="Commit locally only")
    args = parser.parse_args()

    if not args.skip_tests:
        print("Running tests…")
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        _run([sys.executable, "-m", "pytest", "tests/", "-q"], check=True)

    if not args.release_only:
        if not args.message:
            print("ERROR: commit message required unless --release-only")
            return 1
        if not _git_has_changes():
            print("No changes to commit.")
        else:
            _run(["git", "add", "-A"])
            _run(["git", "commit", "-m", args.message])

        if not args.no_push:
            _run(["git", "push", "origin", "main"])

    if args.no_release and not args.release_only:
        print("Done (no release).")
        return 0

    print("Publishing release (agent --yes)…")
    release_cmd = [sys.executable, str(ROOT / "scripts" / "release.py"), "--yes"]
    if args.no_push:
        release_cmd.append("--no-push")
    if args.skip_tests:
        release_cmd.append("--skip-tests")
    _run(release_cmd)
    print("Ship complete.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Agent ship failed: {exc}")
        sys.exit(1)
