"""Tests for build step enrichment."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.build_orders.models import BuildStep
from src.build_orders.step_enricher import enrich_steps


def test_splits_house_and_feudal():
    steps = [BuildStep(
        index=1,
        description="7th vill build house then lure boar click feudal at 7:00",
        time_str="7:00",
        time_sec=420,
    )]
    result = enrich_steps(steps)
    descriptions = " ".join(s.description for s in result)
    assert "house" in descriptions.lower() or "House" in descriptions
    assert len(result) >= 2
