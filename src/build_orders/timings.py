"""
TRINKER - Ideal Timings & Benchmarks
Pre-loaded pro-level benchmarks and helpers for evaluating player performance.
Data sourced from aoe2.gg top players (Hera, Viper, Liereyy, etc.) and community wikis.
"""

from dataclasses import dataclass
from typing import Optional

from ..core.database import db_conn
from ..core.logger import logger

# ---------------------------------------------------------------------------
# Timing evaluation thresholds
# ---------------------------------------------------------------------------

# If player is within these percentages of the benchmark range, classify as:
#   Green  = on pace (within 0-10% slower than benchmark max)
#   Yellow = slightly behind (10-25% slower)
#   Red    = behind (>25% slower)
GREEN_THRESHOLD = 1.10  # up to 10% over benchmark max → green
YELLOW_THRESHOLD = 1.25  # up to 25% over → yellow


@dataclass
class TimingBenchmark:
    """A single timing benchmark record from the ideal_timings table."""

    id: int
    civ: str
    strategy: str
    pop_count: Optional[int]
    feudal_min_sec: Optional[int]
    feudal_max_sec: Optional[int]
    castle_min_sec: Optional[int]
    castle_max_sec: Optional[int]
    imperial_min_sec: Optional[int]
    imperial_max_sec: Optional[int]
    source: str
    notes: str

    def feudal_range_str(self) -> str:
        if self.feudal_min_sec and self.feudal_max_sec:
            return f"{_sec_to_mmss(self.feudal_min_sec)}–{_sec_to_mmss(self.feudal_max_sec)}"
        return "N/A"

    def castle_range_str(self) -> str:
        if self.castle_min_sec and self.castle_max_sec:
            return f"{_sec_to_mmss(self.castle_min_sec)}–{_sec_to_mmss(self.castle_max_sec)}"
        return "N/A"


def _sec_to_mmss(sec: int) -> str:
    """Convert seconds to 'M:SS' display string."""
    return f"{sec // 60}:{sec % 60:02d}"


# ---------------------------------------------------------------------------
# Database queries
# ---------------------------------------------------------------------------


def get_all_benchmarks() -> list[TimingBenchmark]:
    """Return all ideal timing benchmarks from the database."""
    with db_conn() as conn:
        rows = conn.execute("SELECT * FROM ideal_timings ORDER BY civ, strategy").fetchall()
    return [TimingBenchmark(**dict(row)) for row in rows]


def get_benchmarks_for(civ: str, strategy: str) -> list[TimingBenchmark]:
    """
    Return benchmarks matching civ (or 'Any') and strategy (substring match).
    Ordered by specificity: exact civ match before 'Any'.
    """
    with db_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM ideal_timings
               WHERE (civ = ? OR civ = 'Any')
                 AND strategy LIKE ?
               ORDER BY CASE WHEN civ = ? THEN 0 ELSE 1 END""",
            (civ, f"%{strategy}%", civ),
        ).fetchall()
    return [TimingBenchmark(**dict(row)) for row in rows]


def add_custom_benchmark(
    civ: str,
    strategy: str,
    pop_count: Optional[int] = None,
    feudal_min_sec: Optional[int] = None,
    feudal_max_sec: Optional[int] = None,
    castle_min_sec: Optional[int] = None,
    castle_max_sec: Optional[int] = None,
    imperial_min_sec: Optional[int] = None,
    imperial_max_sec: Optional[int] = None,
    notes: str = "",
) -> int:
    """Insert a user-defined benchmark; returns the new row id."""
    with db_conn() as conn:
        cur = conn.execute(
            """INSERT INTO ideal_timings
               (civ, strategy, pop_count, feudal_min_sec, feudal_max_sec,
                castle_min_sec, castle_max_sec, imperial_min_sec, imperial_max_sec,
                source, notes)
               VALUES (?,?,?,?,?,?,?,?,?,'Custom',?)""",
            (
                civ,
                strategy,
                pop_count,
                feudal_min_sec,
                feudal_max_sec,
                castle_min_sec,
                castle_max_sec,
                imperial_min_sec,
                imperial_max_sec,
                notes,
            ),
        )
        return cur.lastrowid


# ---------------------------------------------------------------------------
# Performance evaluation helpers
# ---------------------------------------------------------------------------


def evaluate_feudal_time(
    actual_sec: int,
    benchmark: TimingBenchmark,
) -> tuple[str, str]:
    """
    Compare actual feudal time against a benchmark.

    Returns:
        (status, message) where status is 'green' | 'yellow' | 'red'.
    """
    if benchmark.feudal_max_sec is None:
        return "green", "No feudal benchmark for this build."

    max_b = benchmark.feudal_max_sec
    diff = actual_sec - max_b

    if actual_sec <= max_b:
        status = "green"
        msg = f"On pace! ({_sec_to_mmss(actual_sec)} vs target {benchmark.feudal_range_str()})"
    elif actual_sec <= max_b * GREEN_THRESHOLD:
        status = "green"
        msg = f"Slightly early — great! {_sec_to_mmss(actual_sec)}"
    elif actual_sec <= max_b * YELLOW_THRESHOLD:
        status = "yellow"
        msg = f"+{diff}s behind pace ({_sec_to_mmss(actual_sec)} vs {benchmark.feudal_range_str()})"
    else:
        status = "red"
        msg = f"+{diff}s behind — focus on eco! ({_sec_to_mmss(actual_sec)} vs {benchmark.feudal_range_str()})"

    logger.debug("Feudal eval: %s → %s", actual_sec, status)
    return status, msg


def evaluate_castle_time(
    actual_sec: int,
    benchmark: TimingBenchmark,
) -> tuple[str, str]:
    """Evaluate castle time against benchmark; same logic as feudal."""
    if benchmark.castle_max_sec is None:
        return "green", "No castle benchmark for this build."

    max_b = benchmark.castle_max_sec
    diff = actual_sec - max_b

    if actual_sec <= max_b * GREEN_THRESHOLD:
        status = "green"
        msg = f"Castle on pace! ({_sec_to_mmss(actual_sec)} vs {benchmark.castle_range_str()})"
    elif actual_sec <= max_b * YELLOW_THRESHOLD:
        status = "yellow"
        msg = f"+{diff}s behind castle pace ({_sec_to_mmss(actual_sec)})"
    else:
        status = "red"
        msg = f"+{diff}s behind castle — check eco priorities! ({_sec_to_mmss(actual_sec)})"

    return status, msg


def calculate_accuracy_score(
    steps_completed: int,
    total_steps: int,
    feudal_delta_sec: Optional[int] = None,
    castle_delta_sec: Optional[int] = None,
) -> float:
    """
    Compute a 0–100 accuracy score for a practice session.

    Factors:
      - Step completion ratio (50%)
      - Feudal time delta (25%) — up to 120s penalty
      - Castle time delta (25%) — up to 120s penalty
    """
    if total_steps == 0:
        return 0.0

    step_score = (steps_completed / total_steps) * 50.0

    def timing_score(delta: Optional[int]) -> float:
        if delta is None:
            return 25.0  # give full points if not tracked
        penalty = min(abs(delta), 120) / 120.0
        return 25.0 * (1.0 - penalty)

    score = step_score + timing_score(feudal_delta_sec) + timing_score(castle_delta_sec)
    return round(min(score, 100.0), 1)
