"""
TRINKER - Post-Game Auto-Coach Pipeline
Replay → timeline → historical context → Ollama → coaching report + next-match alert.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from ..analytics.history import build_historical_summary, compare_to_pro_benchmark, get_recurring_themes
from ..build_orders.manager import get_all_build_orders
from ..core.config import settings
from ..core.logger import logger
from ..replay.analyzer import ReplayAnalysis, analyze_replay
from ..replay.mgz_parser import MgzParseResult, parse_with_mgz
from .coach import _is_ollama_available, _offline_coaching_tips

try:
    import requests as _requests
except ImportError:
    _requests = None


HERA_SYSTEM_PROMPT = """You are a Hera-level Age of Empires II: DE coach. You analyze parsed replay data and practice history.

Your job:
1. Compare the player's execution to ideal pro-level Dark/Feudal/Castle transitions.
2. Highlight MICRO decisions: TC idle time, house timing, boar lure, 2nd boar, villager assignments at age-ups, military queue gaps, scouting, walling, first military building time.
3. Cross-reference their historical practice data for recurring mistakes.
4. Give exactly 5 concrete, actionable improvements — each one sentence, imperative voice.
5. Suggest ONE build order they should drill next (name it specifically).
6. End with a single OVERLAY ALERT line (max 12 words) they must see before their next game with this build — the #1 mistake to not repeat.

Format your response EXACTLY:
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


@dataclass
class PostGameCoachResult:
    report: str
    suggested_build: str = ""
    overlay_alert: str = ""
    used_ai: bool = False
    timeline: str = ""
    historical: str = ""


def build_replay_timeline(path: str, analysis: Optional[ReplayAnalysis] = None) -> str:
    """2.0 validated replay profile formatted for LLM coaching."""
    from ..replay.profile import extract_replay_profile

    profile = extract_replay_profile(path)
    lines = [profile.coach_context()]
    if not profile.has_timings():
        lines.append(
            "\nNOTE: Age-up timings not available on this DE patch. "
            "Coach using civ, mode, labels, and practice history only. "
            "Do not invent feudal/castle times."
        )
    return "\n".join(lines)


def _query_ollama_chat(system: str, user: str) -> str:
    if not _requests:
        raise RuntimeError("requests not available")
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0.25, "num_predict": 800},
    }
    resp = _requests.post(f"{settings.ollama_url}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "").strip()


def _parse_overlay_alert(report: str) -> str:
    marker = "## Overlay Alert"
    if marker.lower() not in report.lower():
        return ""
    idx = report.lower().find(marker.lower())
    tail = report[idx + len(marker):].strip()
    for line in tail.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line[:120]
    return ""


def _parse_suggested_build(report: str) -> str:
    for line in report.splitlines():
        if line.lower().startswith("build:"):
            return line.split(":", 1)[-1].strip()
    return ""


def run_postgame_coach(
    replay_path: str,
    civ: str = "Any",
    strategy: str = "",
    build_order_id: Optional[int] = None,
    build_order_name: str = "",
) -> PostGameCoachResult:
    """
    Full post-game pipeline: parse replay, gather history, generate coaching.
    """
    analysis = analyze_replay(replay_path)
    timeline = build_replay_timeline(replay_path, analysis)
    civ = analysis.civ if analysis.civ != "Unknown" else civ

    historical = build_historical_summary(civ, build_order_id)
    pro_cmp = compare_to_pro_benchmark(
        civ, strategy or "Fast Castle",
        analysis.feudal_time_sec, analysis.castle_time_sec,
    )

    user_prompt = f"""{timeline}

{historical}

{pro_cmp}

Build practiced: {build_order_name or 'Unknown'}
Strategy: {strategy or 'Unknown'}

Analyze this game and give your coaching report."""

    if not _is_ollama_available():
        offline = _offline_coaching_tips(
            analysis.feudal_time_sec, analysis.castle_time_sec, None,
        )
        alert = "Queue vills non-stop — never idle your TC"
        if analysis.feudal_time_sec and analysis.feudal_time_sec > 600:
            alert = "Click Feudal earlier — you were late again"
        return PostGameCoachResult(
            report=offline,
            suggested_build="18 Vills Scout Rush",
            overlay_alert=alert,
            used_ai=False,
            timeline=timeline,
            historical=historical,
        )

    try:
        report = _query_ollama_chat(HERA_SYSTEM_PROMPT, user_prompt)
        alert = _parse_overlay_alert(report)
        suggested = _parse_suggested_build(report)
        logger.info("Post-game coach generated (%d chars)", len(report))
        return PostGameCoachResult(
            report=report,
            suggested_build=suggested,
            overlay_alert=alert or "Focus on one clean feudal timing",
            used_ai=True,
            timeline=timeline,
            historical=historical,
        )
    except Exception as exc:
        logger.warning("Post-game coach failed: %s", exc)
        return PostGameCoachResult(
            report=f"AI coach error: {exc}\n\n{timeline}",
            overlay_alert="Check TRINKER Settings → Ollama connection",
            used_ai=False,
            timeline=timeline,
            historical=historical,
        )


def pin_overlay_alert(alert: str, build_order_id: Optional[int] = None) -> None:
    """Save coaching alert for display on overlay next match."""
    settings.overlay_coach_alert = alert
    settings.overlay_coach_alert_bo_id = build_order_id
    settings.save()
    logger.info("Overlay alert pinned: %s", alert[:60])


def create_postgame_worker(
    replay_path: str,
    civ: str,
    strategy: str,
    bo_id: Optional[int],
    bo_name: str,
):
    """Factory for a QObject worker suitable for QThread background coaching."""
    from PySide6.QtCore import QObject, Signal

    class _PostGameCoachWorker(QObject):
        finished = Signal(object)
        error = Signal(str)

        def __init__(self):
            super().__init__()
            self.replay_path = replay_path
            self.civ = civ
            self.strategy = strategy
            self.bo_id = bo_id
            self.bo_name = bo_name

        def run(self) -> None:
            try:
                result = run_postgame_coach(
                    self.replay_path, self.civ, self.strategy,
                    self.bo_id, self.bo_name,
                )
                self.finished.emit(result)
            except Exception as exc:
                self.error.emit(str(exc))

    return _PostGameCoachWorker()
