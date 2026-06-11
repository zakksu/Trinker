"""
TRINKER 2.0 — Premium granular build orders with micro-step player guidance.
"""

from __future__ import annotations

from .importer import _mmss_to_sec
from .models import BuildOrder, BuildStep


def _s(
    idx: int,
    desc: str,
    time_str: str = "",
    pop: int = 0,
    *,
    food=None,
    wood=None,
    gold=None,
    stone=None,
    age=None,
    notes: str = "",
) -> BuildStep:
    return BuildStep(
        index=idx,
        description=desc,
        time_str=time_str,
        time_sec=_mmss_to_sec(time_str) if time_str else 0,
        population=pop,
        food=food,
        wood=wood,
        gold=gold,
        stone=stone,
        age=age,
        notes=notes,
    )


def britons_archer_rush_detailed() -> BuildOrder:
    """22-pop Britons archer rush — ~32 micro-steps with Dark/Feudal/Castle guidance."""
    steps = [
        # ── Dark Age opening ──────────────────────────────────────────────
        _s(
            1,
            "Queue 2 villagers from TC. Research Loom.",
            "0:00",
            4,
            food=6,
            notes="Britons sheep last longer — prioritize sheep + boars. Never idle TC.",
        ),
        _s(2, "Send 6 villagers to nearest sheep.", "0:05", 4, food=6),
        _s(
            3,
            "Scout: find 2 sheep groups + both boars + berries.",
            "0:10",
            4,
            notes="Circle map; note enemy location for later archer attack",
        ),
        _s(4, "7th vill: build house, then send to sheep.", "0:25", 7, food=7),
        _s(5, "8th vill -> sheep.", "0:50", 8, food=8),
        _s(
            6,
            "9th vill -> sheep. Start luring 1st boar to TC.",
            "1:10",
            9,
            food=9,
            notes="Pull boar under TC at low HP; use scout to help if needed",
        ),
        _s(7, "10th vill -> boar (under TC).", "1:30", 10, food=10),
        _s(
            8,
            "Build house at pop 11–12 if not done.",
            "2:00",
            10,
            notes="Always stay 1 house ahead of pop cap",
        ),
        _s(
            9,
            "11th vill -> build Lumber Camp on best woodline -> wood.",
            "2:15",
            11,
            wood=3,
        ),
        _s(10, "12th vill -> wood.", "2:35", 12, wood=4),
        _s(11, "13th vill -> wood.", "2:55", 13, wood=5),
        _s(
            12,
            "Lure 2nd boar to TC while woodline fills.",
            "3:10",
            13,
            notes="After 1st boar ~half depleted or while luring",
        ),
        _s(13, "14th vill -> build Mill on berries -> berries.", "3:30", 14, wood=5),
        _s(14, "15th vill -> berries.", "3:50", 15, food=6, wood=5),
        _s(15, "16th vill -> berries.", "4:10", 16, food=8, wood=5),
        _s(16, "17th vill -> wood (target 6 on wood).", "4:30", 17, wood=6),
        _s(17, "18th vill -> build Mining Camp -> gold.", "4:50", 18, gold=1, wood=6),
        _s(18, "19th vill -> gold.", "5:10", 19, gold=2, wood=6),
        _s(
            19,
            "Research Double-Bit Axe when you have 200 wood.",
            "5:30",
            19,
            wood=4,
            gold=2,
            notes="Huge payoff — queue when wood floats",
        ),
        _s(20, "20th vill -> gold (3 total on gold).", "5:50", 20, gold=3, wood=5),
        _s(21, "21st vill -> wood or berries.", "6:10", 21, gold=3, wood=6),
        _s(
            22,
            "22nd vill -> farm under TC or berries.",
            "6:30",
            22,
            gold=3,
            wood=6,
            food=8,
        ),
        _s(23, "Build house before Feudal click if pop capped.", "6:45", 22),
        _s(
            24,
            "Click Feudal Age (500 food). Shift 2 vills to gold.",
            "7:15",
            22,
            gold=3,
            notes="Target Feudal arrival: 9:15–9:45. Ideal benchmark: 9:30",
        ),
        # ── Feudal transition & attack ────────────────────────────────────
        _s(
            25,
            "During Feudal up: 2 vills build Barracks (Feudal req).",
            "7:15",
            22,
            age="Feudal",
            notes="Place Barracks forward but safe",
        ),
        _s(
            26,
            "During Feudal up: 2 vills build Archery Range.",
            "7:20",
            22,
            notes="Range near forward Barracks — production starts instantly",
        ),
        _s(
            27,
            "Feudal arrives — queue Archers non-stop from Range.",
            "9:30",
            24,
            gold=4,
            age="Feudal",
            notes="Britons: plan Fletching + Thumb Ring later",
        ),
        _s(
            28,
            "Research Fletching (3-shot villagers).",
            "10:00",
            25,
            gold=4,
            notes="Priority upgrade — huge power spike",
        ),
        _s(29, "Build 2nd Archery Range at 8–10 archers.", "10:30", 26, gold=5),
        _s(
            30,
            "Send 8–10 archers + scout to enemy wood/gold.",
            "11:00",
            28,
            gold=5,
            notes="Target villagers, not units. Add archers as they spawn",
        ),
        _s(
            31,
            "New vills -> farms + gold (5–6 on gold total).",
            "11:30",
            30,
            gold=6,
            notes="Maintain constant archer production from 2 ranges",
        ),
        _s(
            32,
            "Click Castle Age at 800F / 200G (~15 archers on field).",
            "13:30",
            32,
            gold=6,
        ),
        # ── Castle follow-up ──────────────────────────────────────────────
        _s(
            33,
            "Castle arrives — Britons ranges 20% faster. Spam Crossbowmen.",
            "16:00",
            35,
            age="Castle",
            notes="Research Bodkin Arrow (+1 range). Add Blacksmith upgrades",
        ),
        _s(
            34,
            "Add 3rd Archery Range if ahead. Keep pressure on eco.",
            "17:00",
            38,
            gold=7,
            notes="Britons excel at ranged mass — don't stop archer production",
        ),
    ]
    return BuildOrder(
        name="Britons Archer Rush",
        civ="Britons",
        strategy="Archer Rush",
        difficulty="Medium",
        author="TRINKER Pro Guide",
        external_id="britons-archer-rush",
        source_url="https://www.buildorderguide.com",
        tags=["archer", "rush", "britons", "feudal", "meta", "detailed", "22pop"],
        notes=(
            "22-pop Britons archer rush with full micro guidance. "
            "Target: Feudal ~9:30, Fletching by 10:00, attack by 11:00, Castle ~16:00. "
            "Britons bonus: sheep last 20% longer; Castle Age archery ranges work 20% faster."
        ),
        steps=steps,
    )


def fast_castle_any_detailed() -> BuildOrder:
    """21-pop Fast Castle (Any civ) — skip feudal army, reach Castle ~15:30."""
    steps = [
        # ── Dark Age eco ──────────────────────────────────────────────────
        _s(
            1,
            "Queue 2 villagers from TC. Research Loom.",
            "0:00",
            4,
            food=6,
            notes="Fast Castle = zero feudal military. Eco perfection only.",
        ),
        _s(2, "Send 6 villagers to nearest sheep.", "0:05", 4, food=6),
        _s(
            3,
            "Scout: locate boars, berries, gold, wood, enemy.",
            "0:10",
            4,
            notes="You won't attack in Feudal — scout for later knight timing",
        ),
        _s(4, "7th vill: build house -> sheep.", "0:25", 7, food=7),
        _s(5, "8th–9th vill -> sheep.", "0:50", 9, food=9),
        _s(
            6,
            "Lure 1st boar to TC. 10th vill -> boar.",
            "1:20",
            10,
            food=10,
            notes="Food is king for FC — take both boars",
        ),
        _s(7, "11th vill -> build Lumber Camp -> wood.", "2:10", 11, wood=3),
        _s(8, "12th–13th vill -> wood.", "2:35", 13, wood=5),
        _s(9, "Lure 2nd boar. 14th vill -> boar under TC.", "3:00", 14, food=10, wood=5),
        _s(10, "15th vill -> build Mill on berries -> berries.", "3:30", 15, wood=5),
        _s(11, "16th–17th vill -> berries.", "3:55", 17, food=10, wood=5),
        _s(12, "18th–19th vill -> wood (target 7–8 on wood).", "4:30", 19, wood=7),
        _s(
            13,
            "Research Horse Collar when affordable.",
            "4:50",
            19,
            wood=6,
            notes="Farms become efficient — research before heavy farming",
        ),
        _s(14, "20th vill -> build Mining Camp -> gold.", "5:15", 20, gold=1, wood=7),
        _s(15, "21st vill -> gold.", "5:35", 21, gold=2, wood=7),
        _s(16, "Research Double-Bit Axe at 200 wood.", "5:50", 21, wood=5, gold=2),
        _s(17, "22nd–23rd vill -> gold (4 on gold).", "6:15", 23, gold=4, wood=6),
        _s(
            18,
            "24th–25th vill -> farms under TC.",
            "6:45",
            25,
            gold=4,
            food=10,
            wood=5,
            notes="Shift food from berries to farms as berries deplete",
        ),
        # ── Feudal -> Castle (no military!) ────────────────────────────────
        _s(
            19,
            "Build house. Click Feudal Age at 21–25 pop.",
            "8:00",
            25,
            gold=4,
            notes="Target Feudal: 9:30–10:30. Only Barracks — NO scouts/archers",
        ),
        _s(
            20,
            "During Feudal up: 1–2 vills build Barracks (required).",
            "8:00",
            25,
            age="Feudal",
            notes="Place Barracks but do NOT queue units",
        ),
        _s(
            21,
            "Feudal arrives — click Castle Age IMMEDIATELY (800F/200G).",
            "10:00",
            26,
            age="Feudal",
            notes="Do NOT build Range or Stable in Feudal",
        ),
        _s(
            22,
            "Shift 3+ vills to gold during Castle transition (6–7 on gold).",
            "10:00",
            27,
            gold=6,
            notes="Add farms; keep TC producing vills",
        ),
        _s(
            23,
            "During Castle up: build 2 Stables.",
            "10:30",
            28,
            gold=6,
            wood=8,
            notes="Prepare knight production for Castle arrival",
        ),
        _s(
            24,
            "Castle arrives — queue 4+ Knights from 2 Stables.",
            "15:30",
            30,
            age="Castle",
            notes="Target Castle: 15:00–16:30. Research Bloodlines + Forging",
        ),
        _s(
            25,
            "Add 3rd Stable. New vills -> farms + gold.",
            "16:30",
            33,
            gold=7,
            notes="6+ knights on field before pushing. Add Blacksmith upgrades",
        ),
        # ── Post-Castle ───────────────────────────────────────────────────
        _s(
            26,
            "Research Iron Casting. Push with knight mass.",
            "17:30",
            35,
            gold=7,
            notes="FC wins by timing — hit before enemy Castle power spikes",
        ),
        _s(
            27,
            "Add Monastery or Siege Workshop if enemy walls up.",
            "18:30",
            36,
            notes="Optional: monks to convert knights, rams for towers",
        ),
    ]
    return BuildOrder(
        name="21 Pop Fast Castle (Any)",
        civ="Any",
        strategy="Fast Castle",
        difficulty="Medium",
        author="TRINKER Pro Guide",
        external_id="fast-castle-knights",
        source_url="https://www.buildorderguide.com",
        tags=["fast castle", "knight", "fc", "castle", "meta", "detailed", "21pop"],
        notes=(
            "Standard 21–25 pop Fast Castle into Knights. Zero feudal military. "
            "Target: Feudal ~10:00, Castle ~15:30, knight flood by 17:00. "
            "Works on any civ — swap knights for your civ's Castle power unit if preferred."
        ),
        steps=steps,
    )


PREMIUM_BUILDS = [
    britons_archer_rush_detailed,
    fast_castle_any_detailed,
]
