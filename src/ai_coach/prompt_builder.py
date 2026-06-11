"""
TRINKER - Structured AI prompt builder for coaching.
Centralizes system/user prompts for session, post-game, and chat coaching.
"""

from __future__ import annotations

from typing import Optional

from .summary import ReplaySummary

COACH_SYSTEM_PROMPT = """You are an expert Age of Empires II: DE coach (Hera-level analysis).
You receive structured game data and practice history. Be direct, actionable, and concise.
Focus on eco, age-up timings, military transitions, and recurring mistakes.
Never invent timings that are marked unavailable in the data."""

SESSION_FORMAT = """Provide 3-5 specific improvement tips in this format:
1. [Biggest issue — one sentence, imperative]
2. [Next priority]
3. [Timing/eco optimization]
(add up to 2 more if clearly relevant)
Keep each tip under 2 sentences."""

POSTGAME_FORMAT = """Format your response EXACTLY:
## Brief Report
(2-3 sentences max)

## 5 Improvements
1. ...
2. ...
3. ...
4. ...
5. ...

## Practice Next
Build: [name] — [one sentence why]

## Overlay Alert
[12 words or fewer — punchy reminder]"""

CHAT_FORMAT = """Answer the player's question using the game context provided.
If data is missing, say so and give general advice for their civ/build.
Keep responses under 200 words unless they ask for detail."""


class PromptBuilder:
    """Build structured prompts from ReplaySummary and stats dicts."""

    @staticmethod
    def session_coaching(summary: ReplaySummary) -> tuple[str, str]:
        user = f"""{summary.to_context_block()}

Analyze this practice session. {SESSION_FORMAT}"""
        return COACH_SYSTEM_PROMPT, user

    @staticmethod
    def postgame_coaching(summary: ReplaySummary) -> tuple[str, str]:
        system = COACH_SYSTEM_PROMPT + "\n\n" + POSTGAME_FORMAT
        user = f"""{summary.to_context_block()}

Analyze this game and give your coaching report."""
        return system, user

    @staticmethod
    def build_recommendations(stats: dict, top_mistakes: list[str]) -> str:
        mistakes_str = "\n".join(f"  - {m}" for m in top_mistakes[:5]) if top_mistakes else "  None"
        feudal = stats.get("avg_feudal_sec")
        castle = stats.get("avg_castle_sec")
        return f"""You are an AoE2 coaching AI. Based on this player's stats, recommend 2-3 build orders to practice.

Stats:
- Sessions: {stats.get('total_sessions', 0)}
- Win rate: {stats.get('win_rate', 0):.1f}%
- Avg Feudal: {_mmss(feudal)}
- Avg Castle: {_mmss(castle)}
- Best Feudal: {_mmss(stats.get('best_feudal_sec'))}

Recurring mistakes:
{mistakes_str}

Name concrete builds and explain in one sentence why each helps."""

    @staticmethod
    def chat_question(summary: ReplaySummary, question: str, history: list[tuple[str, str]]) -> tuple[str, str]:
        hist_lines = []
        for role, content in history[-6:]:
            label = "Player" if role == "user" else "Coach"
            hist_lines.append(f"{label}: {content[:500]}")
        hist_block = "\n".join(hist_lines) if hist_lines else "(no prior messages)"

        user = f"""Context:
{summary.to_context_block()}

Recent chat:
{hist_block}

Player question: {question}

{CHAT_FORMAT}"""
        return COACH_SYSTEM_PROMPT, user


def _mmss(sec: Optional[int]) -> str:
    if sec is None:
        return "N/A"
    return f"{sec // 60}:{sec % 60:02d}"
