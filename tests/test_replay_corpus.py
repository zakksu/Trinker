"""Replay corpus regression tests."""

import pytest

from tests.fixtures.corpus_runner import run_corpus_assertions


@pytest.mark.corpus
def test_replay_corpus_manifest(replay_corpus_dir):
    results = run_corpus_assertions(replay_corpus_dir)
    assert results, "manifest produced no entries"
    failures = [r for r in results if not r.ok]
    assert not failures, "; ".join(f"{r.replay_id}: {r.detail}" for r in failures)
