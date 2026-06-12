"""Update service tests."""

from pathlib import Path
from unittest.mock import patch

from src.core.update_service import UpdateStatus, apply_git_pull, check_updates


def test_update_status_properties():
    st = UpdateStatus(local_version="3.1.0", git_behind=2)
    assert st.has_git_update
    assert st.has_any_update
    assert "2 commit" in st.summary()


def test_check_updates_no_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("src.core.update_service.check_for_update", return_value={"remote_version": None}):
        st = check_updates(tmp_path)
    assert not st.git_available
    assert not st.has_any_update


def test_apply_git_pull_not_repo(tmp_path):
    ok, msg = apply_git_pull(tmp_path)
    assert not ok
    assert "git" in msg.lower()
