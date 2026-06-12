"""Tests for TRINKER sandbox mode (isolated fake training environment)."""

import importlib


def _reload_config(monkeypatch, sandbox: str | None):
    if sandbox is None:
        monkeypatch.delenv("TRINKER_SANDBOX", raising=False)
    else:
        monkeypatch.setenv("TRINKER_SANDBOX", sandbox)
    import src.core.config as config

    importlib.reload(config)
    return config


def test_sandbox_mode_env_values(monkeypatch):
    for val in ("1", "true", "yes", "on", "TRUE"):
        cfg = _reload_config(monkeypatch, val)
        assert cfg.is_sandbox_mode() is True
        assert cfg.APP_NAME == "TRINKER_SANDBOX"


def test_production_mode_when_unset(monkeypatch):
    cfg = _reload_config(monkeypatch, None)
    assert cfg.is_sandbox_mode() is False
    assert cfg.APP_NAME == "TRINKER"


def test_sandbox_uses_separate_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("TRINKER_SANDBOX", "1")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    cfg = _reload_config(monkeypatch, "1")
    assert "TRINKER_SANDBOX" in str(cfg.DATA_DIR)
    assert cfg.DATA_DIR != tmp_path / "TRINKER"


def test_seed_sandbox_script(monkeypatch):
    monkeypatch.setenv("TRINKER_SANDBOX", "1")
    cfg = _reload_config(monkeypatch, "1")
    data_dir = cfg.DATA_DIR

    import src.core.database as db

    importlib.reload(db)

    from scripts.seed_sandbox import main

    assert main() == 0
    assert (data_dir / "trinker.db").exists()
    assert (data_dir / "knowledge" / "hera" / "hera_corpus.md").exists()
