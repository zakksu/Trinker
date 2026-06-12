"""
TRINKER - Post-Game Auto-Coach Pipeline
Replay → timeline → historical context → Ollama → coaching report + next-match alert.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..analytics.compare import compare_to_build_order
from ..analytics.history import build_historical_summary, compare_to_pro_benchmark
from ..core.config import settings
from ..core.logger import logger
from ..replay.analyzer import ReplayAnalysis, analyze_replay
from .coach import _is_ollama_available, _offline_coaching_tips, _query_ollama_chat
from .prompt_builder import PromptBuilder
from .summary import ReplaySummary


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


def _parse_overlay_alert(report: str) -> str:
    marker = "## Overlay Alert"
    if marker.lower() not in report.lower():
        return ""
    idx = report.lower().find(marker.lower())
    tail = report[idx + len(marker) :].strip()
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
        civ,
        strategy or "Fast Castle",
        analysis.feudal_time_sec,
        analysis.castle_time_sec,
    )
    bo_cmp = compare_to_build_order(
        feudal_sec=analysis.feudal_time_sec,
        castle_sec=analysis.castle_time_sec,
        build_order_id=build_order_id,
    )
    cmp_lines = [f"=== Build Comparison ({bo_cmp.build_name}) ===", bo_cmp.summary]
    for row in bo_cmp.rows:
        cmp_lines.append(f"  {row.label}: {row.actual} vs {row.target} [{row.status}]")

    summary = ReplaySummary(
        civ=civ,
        build_name=build_order_name,
        strategy=strategy or "",
        feudal_sec=analysis.feudal_time_sec,
        castle_sec=analysis.castle_time_sec,
        timeline=timeline,
        historical=historical,
        benchmark=pro_cmp,
        comparison="\n".join(cmp_lines),
    )
    system_prompt, user_prompt = PromptBuilder.postgame_coaching(summary)

    if settings.rag_enabled:
        from .rag import retrieve_context

        rag = retrieve_context(
            f"{civ} {strategy} {build_order_name} feudal castle eco",
        )
        if rag:
            user_prompt = f"{user_prompt}\n\n{rag}"

    if not _is_ollama_available():
        offline = _offline_coaching_tips(
            analysis.feudal_time_sec,
            analysis.castle_time_sec,
            None,
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
        report = _query_ollama_chat(system_prompt, user_prompt)
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
                    self.replay_path,
                    self.civ,
                    self.strategy,
                    self.bo_id,
                    self.bo_name,
                )
                self.finished.emit(result)
            except Exception as exc:
                self.error.emit(str(exc))

    return _PostGameCoachWorker()
