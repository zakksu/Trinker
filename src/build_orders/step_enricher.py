"""
TRINKER - Build Step Enricher
Splits vague build-order steps into granular, actionable micro-steps.
Focus: house timing, boar lure, villager redistribution at age-ups.
"""

import re
from typing import Optional

from .models import BuildStep

# Patterns that deserve their own dedicated step when buried in a long sentence
_MICRO_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (
        re.compile(r"build\s+(?:a\s+)?house", re.I),
        "Build house",
        "Queue before pop cap — avoid idle TC time",
    ),
    (
        re.compile(r"lure\s+(?:the\s+)?boar", re.I),
        "Lure boar to TC",
        "Use one vill; pull under TC when low HP",
    ),
    (
        re.compile(r"second\s+boar", re.I),
        "Lure 2nd boar to TC",
        "After first boar depletes or while luring",
    ),
    (
        re.compile(r"click\s+feudal|research\s+feudal|feudal\s+age", re.I),
        "Click Feudal Age",
        "Shift 2–3 vills to gold/wood per build; queue next vills",
    ),
    (
        re.compile(r"click\s+castle|research\s+castle|castle\s+age", re.I),
        "Click Castle Age",
        "Rebalance eco: more farms + gold for your follow-up",
    ),
    (
        re.compile(r"click\s+imperial|research\s+imperial|imperial\s+age", re.I),
        "Click Imperial Age",
        "Bank resources; prep production buildings",
    ),
    (
        re.compile(r"lumber\s+camp", re.I),
        "Build Lumber Camp",
        "Place near best woodline; send vills immediately",
    ),
    (
        re.compile(r"build\s+mill", re.I),
        "Build Mill",
        "On berries or deer; don't idle vills after",
    ),
    (
        re.compile(r"mining\s+camp|gold\s+mine", re.I),
        "Build Mining Camp",
        "3+ vills on gold for feudal/castle research",
    ),
    (
        re.compile(r"barracks", re.I),
        "Build Barracks",
        "Required for Feudal — place early in transition",
    ),
    (
        re.compile(r"stable", re.I),
        "Build Stable",
        "Queue scouts/knights; keep production constant",
    ),
    (
        re.compile(r"archery\s+range", re.I),
        "Build Archery Range",
        "Keep archers queued; maintain gold income",
    ),
    (
        re.compile(r"double[\s-]?bit\s+axe|wheelbarrow|horse\s+collar", re.I),
        "Research eco upgrade",
        "Prioritize when you have float — huge long-term payoff",
    ),
    (
        re.compile(r"queue\s+vill|next\s+vill", re.I),
        "Queue next vill from TC",
        "Never let TC idle",
    ),
    (
        re.compile(r"(\d+)\s*(?:on|to)\s*(?:wood|gold|food|berries|sheep|farm)", re.I),
        "Assign villagers",
        "Match the count in the step — accuracy matters here",
    ),
]


def enrich_steps(steps: list[BuildStep]) -> list[BuildStep]:
    """
    Expand coarse steps into finer micro-steps where patterns are detected.
    Preserves timings from the parent step; splits population hints when present.
    """
    if not steps:
        return steps

    enriched: list[BuildStep] = []
    idx = 1

    for step in steps:
        text = f"{step.description} {step.notes}".strip()
        hits: list[tuple[str, str]] = []

        for pattern, title, hint in _MICRO_PATTERNS:
            if pattern.search(text) and not any(h[0] == title for h in hits):
                hits.append((title, hint))

        if len(hits) <= 1 and len(step.description) < 80:
            step.index = idx
            enriched.append(step)
            idx += 1
            continue

        if not hits:
            step.index = idx
            enriched.append(step)
            idx += 1
            continue

        # Parent overview step
        enriched.append(
            BuildStep(
                index=idx,
                description=step.description,
                time_str=step.time_str,
                time_sec=step.time_sec,
                population=step.population,
                food=step.food,
                wood=step.wood,
                gold=step.gold,
                stone=step.stone,
                notes=step.notes,
                age=step.age,
            )
        )
        idx += 1

        for title, hint in hits:
            enriched.append(
                BuildStep(
                    index=idx,
                    description=f"→ {title}",
                    time_str=step.time_str,
                    time_sec=step.time_sec,
                    population=step.population,
                    notes=hint,
                    age=step.age,
                )
            )
            idx += 1

    return enriched


def infer_age_from_text(text: str) -> Optional[str]:
    t = text.lower()
    if "imperial" in t:
        return "Imperial"
    if "castle" in t and "fast castle" not in t:
        return "Castle"
    if "feudal" in t:
        return "Feudal"
    return None
