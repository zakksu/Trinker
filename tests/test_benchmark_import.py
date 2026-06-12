"""Tests for pro benchmark JSON import."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.build_orders.benchmark_import import import_pro_benchmarks, _BENCHMARKS_FILE


def test_benchmark_json_has_enough_rows():
    assert _BENCHMARKS_FILE.exists()
    payload = json.loads(_BENCHMARKS_FILE.read_text(encoding="utf-8"))
    entries = payload.get("benchmarks", [])
    assert len(entries) >= 20


def test_import_pro_benchmarks_merges_without_error():
    count = import_pro_benchmarks(force=False)
    assert count >= 0
