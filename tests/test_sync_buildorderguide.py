"""Tests for buildorderguide.com bulk sync."""

from unittest.mock import MagicMock, patch

import pytest

from scripts.sync_buildorderguide import (
    _extract_urls_from_html,
    discover_build_urls,
    import_build_url,
    needs_sync,
)
from src.build_orders.models import BuildStep
from src.build_orders.step_enricher import enrich_steps as enrich_steps_fn


SAMPLE_INDEX_HTML = """
<html><body>
<a href="/builds/abc123slug">Build A</a>
<a href="https://www.buildorderguide.com/builds/xyz789slug">Build B</a>
</body></html>
"""

SAMPLE_BUILD_HTML = """
<html><head><title>22 Pop Archer Rush</title></head><body>
<h1>22 Pop Archer Rush</h1>
<table class="steps">
<tr><td>1</td><td>0:00</td><td>6</td><td>Queue 2 vills, build house</td></tr>
<tr><td>2</td><td>2:30</td><td>10</td><td>Lure boar to TC</td></tr>
<tr><td>3</td><td>8:00</td><td>22</td><td>Click feudal age</td></tr>
</table>
</body></html>
"""


def test_extract_urls_from_html():
    urls = _extract_urls_from_html(SAMPLE_INDEX_HTML)
    assert "https://www.buildorderguide.com/builds/abc123slug" in urls
    assert "https://www.buildorderguide.com/builds/xyz789slug" in urls


def test_discover_build_urls_mocked(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    monkeypatch.setattr("scripts.sync_buildorderguide.CACHE_DIR", cache)

    def fetcher(url: str):
        resp = MagicMock()
        resp.text = SAMPLE_INDEX_HTML if "builds" in url else SAMPLE_INDEX_HTML
        resp.raise_for_status = MagicMock()
        return resp

    urls = discover_build_urls(fetcher=fetcher, max_pages=1)
    assert len(urls) >= 2
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


def test_import_build_url_uses_fetcher(monkeypatch, tmp_path):
    cache = tmp_path / "bog_cache"
    monkeypatch.setattr("scripts.sync_buildorderguide.CACHE_DIR", cache)

    url = "https://www.buildorderguide.com/builds/testslug1"

    def fetcher(u: str):
        resp = MagicMock()
        resp.text = SAMPLE_BUILD_HTML
        resp.raise_for_status = MagicMock()
        return resp

    bo_mock = MagicMock()
    bo_mock.steps = [BuildStep(index=1, description="Test", population=6)]

    with patch("scripts.sync_buildorderguide.import_from_buildorderguide", return_value=bo_mock):
        with patch("scripts.sync_buildorderguide.import_and_save"):
            import_build_url(url, fetcher=fetcher, enrich=True)

    assert (cache / "testslug1.html").exists()
