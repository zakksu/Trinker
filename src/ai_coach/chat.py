"""
TRINKER - Ask Coach chat persistence and API.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.config import settings
from ..core.database import db_conn, now_iso
from ..core.logger import logger
from .coach import _is_ollama_available, _offline_coaching_tips, _query_ollama_chat
from .prompt_builder import PromptBuilder
from .summary import ReplaySummary


@dataclass
class CoachMessage:
    id: int
    thread_key: str
    role: str
    content: str
    created_at: str


def save_coach_message(thread_key: str, role: str, content: str) -> int:
    with db_conn() as conn:
        cur = conn.execute(
            """INSERT INTO coach_messages (thread_key, role, content, created_at)
               VALUES (?, ?, ?, ?)""",
            (thread_key, role, content, now_iso()),
        )
        return int(cur.lastrowid)


def get_coach_messages(thread_key: str, limit: int = 50) -> list[CoachMessage]:
    with db_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM coach_messages
               WHERE thread_key = ?
               ORDER BY id ASC LIMIT ?""",
            (thread_key, limit),
        ).fetchall()
    return [
        CoachMessage(
            id=row["id"],
            thread_key=row["thread_key"],
            role=row["role"],
            content=row["content"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def ask_coach(
    question: str,
    summary: ReplaySummary,
    *,
    thread_key: str = "dashboard",
) -> str:
    """
    Send a chat question to the AI coach with game context and history.
    Persists user + assistant messages to the database.
    """
    question = question.strip()
    if not question:
        return "Ask a specific question about your last game or build order."

    save_coach_message(thread_key, "user", question)
    history = [(m.role, m.content) for m in get_coach_messages(thread_key)]

    if settings.rag_enabled:
        from .rag import retrieve_context

        rag = retrieve_context(f"{question} {summary.civ} {summary.build_name}")
        if rag:
            summary = ReplaySummary(
                **{**summary.__dict__, "comparison": (summary.comparison or "") + "\n\n" + rag}
            )

    if not _is_ollama_available():
        reply = _offline_coaching_tips(
            summary.feudal_sec, summary.castle_sec, summary.accuracy_pct,
        )
        save_coach_message(thread_key, "assistant", reply)
        return reply

    system, user = PromptBuilder.chat_question(summary, question, history[:-1])
    try:
        reply = _query_ollama_chat(system, user)
        logger.info("Ask Coach reply (%d chars)", len(reply))
    except Exception as exc:
        logger.warning("Ask Coach failed: %s", exc)
        reply = f"Could not reach Ollama: {exc}\n\n{_offline_coaching_tips(summary.feudal_sec, summary.castle_sec, summary.accuracy_pct)}"

    save_coach_message(thread_key, "assistant", reply)
    return reply


def build_summary_from_latest_replay() -> ReplaySummary:
    """Build ReplaySummary from the most recent stored replay analysis."""
    import json

    from ..analytics.compare import compare_to_build_order
    from ..analytics.history import build_historical_summary, compare_to_pro_benchmark
    from ..analytics.replay_store import get_latest_replay_analysis
    from ..build_orders.manager import get_build_order
    from ..core.config import settings

    latest = get_latest_replay_analysis()
    if not latest:
        return ReplaySummary(
            build_name=get_build_order(settings.last_practice_bo_id).name
            if settings.last_practice_bo_id and get_build_order(settings.last_practice_bo_id)
            else "",
        )

    try:
        data = json.loads(latest.profile_json)
    except Exception:
        data = {}

    feudal = data.get("feudal_time_sec")
    castle = data.get("castle_time_sec")
    imperial = data.get("imperial_time_sec")
    bo = get_build_order(settings.last_practice_bo_id) if settings.last_practice_bo_id else None

    cmp = compare_to_build_order(
        feudal_sec=feudal,
        castle_sec=castle,
        imperial_sec=imperial,
    )
    cmp_text = f"=== Build Comparison ({cmp.build_name}) ===\n{cmp.summary}"
    for row in cmp.rows:
        cmp_text += f"\n  {row.label}: {row.actual} vs {row.target} [{row.status}]"

    benchmark = compare_to_pro_benchmark(
        latest.civ,
        bo.strategy if bo else "Fast Castle",
        feudal,
        castle,
    )

    return ReplaySummary(
        civ=latest.civ,
        map_name=latest.map_name,
        game_mode=latest.game_mode,
        build_name=bo.name if bo else "",
        strategy=bo.strategy if bo else "",
        feudal_sec=feudal,
        castle_sec=castle,
        imperial_sec=imperial,
        data_quality=latest.data_quality,
        timeline=data.get("coach_context", ""),
        historical=build_historical_summary(latest.civ, settings.last_practice_bo_id),
        benchmark=benchmark,
        comparison=cmp_text,
    )
