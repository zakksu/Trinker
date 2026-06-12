"""
TRINKER - Platform stats split: training volume vs ranked results.
Honest metrics when most games are SP practice without mgz winner detection.
"""

from __future__ import annotations

import json
from typing import Optional

from ..core.database import db_conn
from .session import get_summary_stats


def get_platform_stats(build_order_id: Optional[int] = None) -> dict:
    """
    Combined stats for Performance Hub.

    Returns quality-filtered timing stats (via get_summary_stats) plus:
      all_games, sp_games, ranked_decided, ranked_win_rate, replay_wins, replay_losses
    """
    base = get_summary_stats(build_order_id)
    bo_filter = "AND build_order_id = ?" if build_order_id else ""
    params: tuple = (build_order_id,) if build_order_id else ()

    with db_conn() as conn:
        all_row = conn.execute(
            f"SELECT COUNT(*) AS n FROM sessions WHERE 1=1 {bo_filter}",
            params,
        ).fetchone()
        sp_row = conn.execute(
            f"""SELECT COUNT(*) AS n FROM sessions
                WHERE (game_mode = 'sp' OR replay_path LIKE '%SP Replay%') {bo_filter}""",
            params,
        ).fetchone()
        ranked_row = conn.execute(
            f"""SELECT
                    SUM(CASE WHEN result = 'win'  THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) AS losses,
                    SUM(CASE WHEN result = 'draw' THEN 1 ELSE 0 END) AS draws
                FROM sessions
                WHERE result IN ('win', 'loss', 'draw') {bo_filter}""",
            params,
        ).fetchone()

    all_games = int(all_row["n"] or 0) if all_row else 0
    sp_games = int(sp_row["n"] or 0) if sp_row else 0
    rw = int(ranked_row["wins"] or 0) if ranked_row else 0
    rl = int(ranked_row["losses"] or 0) if ranked_row else 0
    rd = int(ranked_row["draws"] or 0) if ranked_row else 0
    decided = rw + rl

    replay_wins, replay_losses = _replay_result_counts()

    base["all_games"] = all_games
    base["sp_games"] = sp_games
    base["mp_games"] = max(0, all_games - sp_games)
    base["ranked_wins"] = rw
    base["ranked_losses"] = rl
    base["ranked_draws"] = rd
    base["ranked_decided"] = decided
    base["ranked_win_rate"] = round(rw / decided * 100, 1) if decided > 0 else None
    base["replay_wins"] = replay_wins
    base["replay_losses"] = replay_losses
    base["replay_decided"] = replay_wins + replay_losses
    base["replay_win_rate"] = (
        round(replay_wins / (replay_wins + replay_losses) * 100, 1)
        if replay_wins + replay_losses > 0
        else None
    )
    return base


def _replay_result_counts() -> tuple[int, int]:
    """Win/loss counts parsed from stored replay profiles (mgz winner when available)."""
    wins = losses = 0
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT profile_json FROM replay_analyses ORDER BY analyzed_at DESC LIMIT 500"
        ).fetchall()
    for row in rows:
        try:
            data = json.loads(row["profile_json"] or "{}")
        except Exception:
            continue
        result = (data.get("result") or "").lower()
        if result == "win":
            wins += 1
        elif result == "loss":
            losses += 1
    return wins, losses


def format_win_rate_label(stats: dict) -> str:
    """Best available win-rate string for KPI cards."""
    for key in ("ranked_win_rate", "replay_win_rate", "win_rate"):
        val = stats.get(key)
        if val is not None:
            return f"{val:.1f}%"
    return "—"
