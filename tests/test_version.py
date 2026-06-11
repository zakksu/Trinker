"""Tests for version and config."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.config import get_app_version


def test_version_readable():
    v = get_app_version()
    assert v
    parts = v.split(".")
    assert len(parts) >= 2
