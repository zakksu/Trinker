#!/usr/bin/env python3
"""
TRINKER 3.0 — Ollama auto-setup helper.

Checks for Ollama, verifies the API, and pulls the recommended model.

Usage:
    python scripts/setup_ollama.py
    python scripts/setup_ollama.py --model llama3.2
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.config import settings  # noqa: E402
from src.core.ollama import ensure_ollama_enabled, is_ollama_running  # noqa: E402


def _print_header() -> None:
    print("=" * 56)
    print("  TRINKER 3.0 — Ollama Setup")
    print("=" * 56)
    print()


def _install_hint() -> None:
    print("Ollama is not installed or not in PATH.")
    print()
    print("  1. Download: https://ollama.ai")
    print("  2. Install and launch Ollama")
    print("  3. Re-run: python scripts/setup_ollama.py")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Setup Ollama for TRINKER AI Coach")
    parser.add_argument(
        "--model",
        default=getattr(settings, "recommended_ollama_model", "llama3.2"),
        help="Model to pull (default from settings)",
    )
    args = parser.parse_args()

    _print_header()

    if not shutil.which("ollama"):
        _install_hint()
        return 1

    print(f"Ollama CLI found: {shutil.which('ollama')}")
    print(f"API URL: {settings.ollama_url}")
    print()

    if not is_ollama_running():
        print("Ollama API not responding — start the Ollama app, then retry.")
        print("  Windows: launch Ollama from Start Menu")
        print("  macOS/Linux: run `ollama serve` in a terminal")
        return 1

    print("Ollama API is online.")
    print(f"Pulling model `{args.model}` (may take several minutes on first run)…")
    print()

    try:
        subprocess.run(["ollama", "pull", args.model], check=True)
    except subprocess.CalledProcessError as exc:
        print(f"Failed to pull model: {exc}")
        return 1

    settings.ollama_model = args.model
    settings.ai_coach_enabled = True
    settings.auto_postgame_coach = True
    settings.save()
    ensure_ollama_enabled()

    print()
    print("Setup complete!")
    print(f"  Model: {args.model}")
    print("  AI Coach enabled in TRINKER Settings.")
    print("  Open TRINKER → Settings → Test Connection to verify.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
