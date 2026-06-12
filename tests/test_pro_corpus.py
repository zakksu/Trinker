"""Tests for pro replay corpus builder."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ai_coach.pro_replay_corpus import (
    _name_matches_pro,
    build_knowledge_markdown,
    ProCorpusResult,
    ProGameRecord,
)
from src.ai_coach.modelfile_builder import build_modelfile_content, model_name


def test_hera_name_match():
    assert _name_matches_pro("Hera", "Hera")
    assert _name_matches_pro("Hera_AoE", "Hera")
    assert not _name_matches_pro("Herald", "Hera")
    assert not _name_matches_pro("RandomPlayer", "Hera")


def test_corpus_markdown_empty():
    result = ProCorpusResult(pro_name="Hera", games=[])
    md = build_knowledge_markdown(result)
    assert "No games found" in md
    assert "pro_replays" in md


def test_corpus_markdown_with_games():
    result = ProCorpusResult(
        pro_name="Hera",
        games=[
            ProGameRecord(
                replay_file="test.aoe2record",
                replay_path="/x",
                player_name="Hera",
                civ="Britons",
                feudal_time_sec=555,
                winner=True,
            )
        ],
    )
    md = build_knowledge_markdown(result)
    assert "Britons" in md
    assert "555" not in md or "9:" in md


def test_modelfile_contains_pro_name():
    result = ProCorpusResult(pro_name="Hera", games=[])
    content = build_modelfile_content(result, base_model="llama3.2")
    assert "FROM llama3.2" in content
    assert "Hera" in content
    assert model_name("Hera") == "trinker-hera"
