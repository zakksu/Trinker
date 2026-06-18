#!/usr/bin/env python3
"""Invoke xAI Grok Build CLI headlessly for TRINKER development tasks."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL_URL = "https://x.ai/news/grok-build-cli"
INSTALL_PS = "irm https://x.ai/cli/install.ps1 | iex"


def _find_grok() -> str | None:
    for name in ("grok-build", "grok"):
        path = shutil.which(name)
        if path:
            return path
    return None


def cmd_check() -> int:
    exe = _find_grok()
    if exe:
        print(f"OK: {exe}")
        return 0
    print("Grok Build CLI not found.")
    print(f"Install: {INSTALL_PS}")
    print(f"Docs:    {INSTALL_URL}")
    print(f"TRINKER: docs/GROK_INTEGRATION.md")
    return 1


def cmd_run(prompt: str, *, plan: bool) -> int:
    exe = _find_grok()
    if not exe:
        return cmd_check()

    cmd = [exe, "-p", prompt]
    if plan:
        cmd = [exe, "--plan", "-p", prompt]

    print(f"$ {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=ROOT)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="TRINKER Grok Build hook")
    parser.add_argument("prompt", nargs="?", default="", help="Task prompt for headless Grok Build")
    parser.add_argument("--check", action="store_true", help="Verify grok-build is installed")
    parser.add_argument("--plan", action="store_true", help="Use Grok plan mode before execution")
    args = parser.parse_args()

    if args.check:
        return cmd_check()
    if not args.prompt:
        parser.error("prompt required unless --check")
    return cmd_run(args.prompt, plan=args.plan)


if __name__ == "__main__":
    raise SystemExit(main())
