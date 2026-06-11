"""
TRINKER - Structured replay summary for AI coaching prompts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ReplaySummary:
    """Compact structured context passed to the AI coach."""

    civ: str = "Unknown"
    map_name: str = ""
    game_mode: str = ""
    build_name: str = ""
    strategy: str = ""
    result: str = "practice"
    feudal_sec: Optional[int] = None
    castle_sec: Optional[int] = None
    imperial_sec: Optional[int] = None
    accuracy_pct: Optional[float] = None
    data_quality: str = ""
    notes: str = ""
    mistakes: list[str] = field(default_factory=list)
    timeline: str = ""
    historical: str = ""
    benchmark: str = ""
    comparison: str = ""

    def to_context_block(self) -> str:
        """Render as a structured block for LLM consumption."""
        lines = [
            "=== Game Summary ===",
            f"Civ: {self.civ}  |  Map: {self.map_name or '—'}  |  Mode: {self.game_mode or '—'}",
            f"Build: {self.build_name or '—'}  |  Strategy: {self.strategy or '—'}",
            f"Result: {self.result}  |  Quality: {self.data_quality or '—'}",
        ]
        if self.feudal_sec is not None:
            lines.append(f"Feudal: {self._mmss(self.feudal_sec)}")
        if self.castle_sec is not None:
            lines.append(f"Castle: {self._mmss(self.castle_sec)}")
        if self.imperial_sec is not None:
            lines.append(f"Imperial: {self._mmss(self.imperial_sec)}")
        if self.accuracy_pct is not None:
            lines.append(f"Accuracy: {self.accuracy_pct:.1f}%")
        if self.mistakes:
            lines.append("Mistakes:")
            lines.extend(f"  - {m}" for m in self.mistakes[:8])
        if self.notes:
            lines.append(f"Notes: {self.notes[:400]}")
        if self.comparison:
            lines.append(self.comparison)
        if self.benchmark:
            lines.append(self.benchmark)
        if self.timeline:
            lines.append(self.timeline)
        if self.historical:
            lines.append(self.historical)
        return "\n".join(lines)

    @staticmethod
    def _mmss(sec: int) -> str:
        return f"{sec // 60}:{sec % 60:02d}"
