#!/usr/bin/env bash
# Build TRINKER with PyInstaller on Linux/macOS (folder bundle, not one-file).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m pip install --upgrade pip -q
python3 -m pip install -r requirements.txt pyinstaller -q
python3 seed_builds.py 2>/dev/null || true

python3 -m PyInstaller trinker.spec --noconfirm

if [[ "$(uname)" == "Darwin" ]]; then
  echo "Build complete: dist/TRINKER.app (or dist/TRINKER)"
else
  echo "Build complete: dist/TRINKER"
fi
