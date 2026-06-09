#!/usr/bin/env bash
# TRINKER launcher script
# Usage: bash run_trinker.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting TRINKER..."
python3 main.py "$@"
