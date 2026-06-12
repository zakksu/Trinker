"""
TRINKER - Simulation engine stub for offline drill timing practice.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimScenario:
    id: str
    title: str
    target_feudal_sec: int
    description: str


_SCENARIOS: dict[str, SimScenario] = {
    "dark_age_eco": SimScenario(
        id="dark_age_eco",
        title="Dark Age Eco Pace",
        target_feudal_sec=480,
        description="Simulate villager queue timing — aim for 22 pop by 8:00.",
    ),
    "scout_open": SimScenario(
        id="scout_open",
        title="Scout Opening",
        target_feudal_sec=540,
        description="Practice feudal click at 9:00 with clean house timing.",
    ),
    "fc_boom": SimScenario(
        id="fc_boom",
        title="Fast Castle Transition",
        target_feudal_sec=600,
        description="Hit Feudal at 10:00, Castle by 15:30 in your head — no game required.",
    ),
}


def list_scenarios() -> list[SimScenario]:
    return list(_SCENARIOS.values())


def get_scenario(scenario_id: str) -> SimScenario | None:
    return _SCENARIOS.get(scenario_id)


def evaluate_tick(scenario: SimScenario, elapsed_sec: int) -> str:
    """Return coaching hint for a simulated elapsed game second."""
    target = scenario.target_feudal_sec
    if elapsed_sec <= 0:
        return "Start the sim timer and mentally execute your build order."
    if elapsed_sec < target - 60:
        return f"On pace — Feudal target in {_fmt(target - elapsed_sec)}."
    if elapsed_sec < target:
        return f"Feudal window opening — click up in {_fmt(target - elapsed_sec)}."
    if elapsed_sec <= target + 30:
        return "Feudal window — you should be clicking now."
    late = elapsed_sec - target
    return f"Late by {_fmt(late)} — identify where TC idle or house delay happened."


def _fmt(sec: int) -> str:
    m, s = divmod(max(0, sec), 60)
    return f"{m}:{s:02d}"
