"""Tests for buildorderguide.com bulk sync (Firestore card/modal site)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.sync_buildorderguide import (
    discover_build_urls,
    import_build_url,
    needs_sync,
)
from src.build_orders.bog_firestore import (
    bog_step_to_description,
    build_order_from_bog_data,
    decode_firestore_doc,
)
from src.build_orders.models import BuildStep
from src.build_orders.step_enricher import enrich_steps as enrich_steps_fn

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "buildorderguide"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_bog_step_to_description_new_villagers():
    step = {"type": "newVillagers", "count": 6, "task": "sheep", "buildings": [{"type": "house", "count": 2}]}
    text = bog_step_to_description(step)
    assert "6" in text
    assert "Sheep" in text
    assert "House" in text


def test_decode_firestore_listing_doc():
    doc = _load_json("firestore_listing_doc.json")
    data = decode_firestore_doc(doc)
    assert data["id"] == "abc123slug"
    assert data["title"] == "22 Pop Archer Rush"
    assert data["status"] == "published"


def test_build_order_from_firestore_detail():
    doc = _load_json("firestore_detail_doc.json")
    data = decode_firestore_doc(doc)
    bo = build_order_from_bog_data(data)
    assert bo.name == "22 Pop Archer Rush"
    assert bo.civ == "Britons"
    assert bo.external_id == "abc123slug"
    assert len(bo.steps) >= 3
    assert "vill" in bo.steps[0].description.lower()


def test_discover_build_urls_firestore_mocked(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    monkeypatch.setattr("scripts.sync_buildorderguide.CACHE_DIR", cache)

    with patch(
        "scripts.sync_buildorderguide.firestore_discover_urls",
        return_value=[
            "https://www.buildorderguide.com/builds/abc123slug",
            "https://www.buildorderguide.com/builds/xyz789slug",
        ],
    ):
        urls = discover_build_urls()
    assert len(urls) == 2
    assert (cache / "manifest.json").exists()


def test_enrich_steps_expands_coarse_steps():
    steps = [
        BuildStep(index=1, description="Queue vills and build house", population=6),
        BuildStep(index=2, description="Lure boar and click feudal age", population=22),
    ]
    enriched = enrich_steps_fn(steps)
    assert len(enriched) >= len(steps)


def test_needs_sync_empty_db(monkeypatch, tmp_path):
    monkeypatch.setenv("TRINKER_SANDBOX", "1")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    import importlib

    import src.core.config as cfg

    importlib.reload(cfg)
    import src.core.database as db

    importlib.reload(db)
    db.init_db()
    assert needs_sync(min_builds=50) is True


def test_import_build_url_uses_firestore(tmp_path, monkeypatch):
    cache = tmp_path / "bog_cache"
    monkeypatch.setattr("scripts.sync_buildorderguide.CACHE_DIR", cache)

    url = "https://www.buildorderguide.com/builds/abc123slug"
    detail = decode_firestore_doc(_load_json("firestore_detail_doc.json"))

    with patch("scripts.sync_buildorderguide.fetch_published_build", return_value=detail):
        with patch("scripts.sync_buildorderguide.import_and_save") as save_mock:
            import_build_url(url, enrich=True)

    assert (cache / "abc123slug.json").exists()
    save_mock.assert_called_once()
    saved = save_mock.call_args[0][0]
    assert saved.name == "22 Pop Archer Rush"
    assert len(saved.steps) >= 3
