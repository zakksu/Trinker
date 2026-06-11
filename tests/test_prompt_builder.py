"""Tests for structured AI prompts."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ai_coach.prompt_builder import PromptBuilder
from src.ai_coach.summary import ReplaySummary


def test_replay_summary_context():
    s = ReplaySummary(civ="Spanish", build_name="Scout Rush", feudal_sec=540)
    block = s.to_context_block()
    assert "Spanish" in block
    assert "9:00" in block


def test_session_prompt_structure():
    s = ReplaySummary(civ="Britons", build_name="MAA", feudal_sec=510)
    system, user = PromptBuilder.session_coaching(s)
    assert "coach" in system.lower()
    assert "Britons" in user
    assert "1." in user
