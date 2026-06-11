"""
TRINKER 2.0 - Replay data validation and quality scoring.
Rejects impossible timings before they pollute analytics or AI coaching.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Realistic AoE2 age-up windows (seconds)
FEUDAL_MIN, FEUDAL_MAX = 420, 1020  # 7:00 – 17:00
CASTLE_MIN, CASTLE_MAX = 660, 2100  # 11:00 – 35:00
IMPERIAL_MIN, IMPERIAL_MAX = 1200, 4200
DURATION_MIN, DURATION_MAX = 300, 7200  # 5 min – 2 hours


@dataclass
class ValidatedTimings:
    feudal_time_sec: Optional[int] = None
    castle_time_sec: Optional[int] = None
    imperial_time_sec: Optional[int] = None
    duration_sec: Optional[int] = None
    quality: str = "rejected"  # rejected | low | medium | high
    issues: list[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []

    def has_usable_timings(self) -> bool:
        return self.quality in ("medium", "high") and bool(
            self.feudal_time_sec or self.castle_time_sec
        )


def _clamp_age(
    value: Optional[int],
    lo: int,
    hi: int,
    label: str,
    issues: list[str],
) -> Optional[int]:
    if value is None:
        return None
    if value < lo or value > hi:
        issues.append(f"{label} {value}s outside {lo}-{hi}s")
        return None
    return value


def validate_timings(
    *,
    feudal: Optional[int] = None,
    castle: Optional[int] = None,
    imperial: Optional[int] = None,
    duration: Optional[int] = None,
    source: str = "unknown",
) -> ValidatedTimings:
    """Sanitize and score extracted replay timings."""
    issues: list[str] = []
    v = ValidatedTimings(issues=issues)

    v.feudal_time_sec = _clamp_age(feudal, FEUDAL_MIN, FEUDAL_MAX, "Feudal", issues)
    v.castle_time_sec = _clamp_age(castle, CASTLE_MIN, CASTLE_MAX, "Castle", issues)
    v.imperial_time_sec = _clamp_age(imperial, IMPERIAL_MIN, IMPERIAL_MAX, "Imperial", issues)

    if duration is not None:
        if DURATION_MIN <= duration <= DURATION_MAX:
            v.duration_sec = duration
        else:
            issues.append(f"Duration {duration}s invalid")
            v.duration_sec = None

    # Ordering checks
    if v.feudal_time_sec and v.castle_time_sec and v.castle_time_sec <= v.feudal_time_sec + 120:
        issues.append("Castle too close after Feudal")
        v.castle_time_sec = None
    if v.castle_time_sec and v.imperial_time_sec and v.imperial_time_sec <= v.castle_time_sec + 180:
        issues.append("Imperial too close after Castle")
        v.imperial_time_sec = None

    timing_count = sum(1 for t in (v.feudal_time_sec, v.castle_time_sec, v.imperial_time_sec) if t)
    if timing_count >= 2 and source == "mgz":
        v.quality = "high"
    elif timing_count >= 1:
        v.quality = "medium" if source in ("mgz", "scan") else "low"
    elif v.duration_sec and source == "metadata":
        v.quality = "low"
    else:
        v.quality = "rejected"

    return v
