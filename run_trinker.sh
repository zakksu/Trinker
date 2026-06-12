#!/usr/bin/env bash
# TRINKER launcher for Linux and macOS
# Usage: bash run_trinker.sh
#        ./run_trinker.sh   (after chmod +x run_trinker.sh)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: Python 3.11+ is required but '$PYTHON' was not found."
  echo "Install from https://www.python.org/downloads/ or your package manager."
  exit 1
fi

PY_VER="$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="${PY_VER%%.*}"
PY_MINOR="${PY_VER#*.}"
if [[ "$PY_MAJOR" -lt 3 ]] || { [[ "$PY_MAJOR" -eq 3 ]] && [[ "$PY_MINOR" -lt 11 ]]; }; then
  echo "ERROR: Python 3.11+ required (found $PY_VER)."
  exit 1
fi

VENV_DIR="${TRINKER_VENV:-$SCRIPT_DIR/.venv}"
if [[ ! -d "$VENV_DIR" ]]; then
  echo "[1/4] Creating virtual environment at $VENV_DIR …"
  "$PYTHON" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[2/4] Installing dependencies …"
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q

echo "[3/4] Seeding build orders (if needed) …"
python seed_builds.py 2>/dev/null || true

echo "[4/4] Starting TRINKER …"
echo "Data folder: $(python -c 'from src.core.config import DATA_DIR; print(DATA_DIR)')"
exec python main.py "$@"
