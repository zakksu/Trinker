"""
TRINKER — Seed 15 real AoE2 build orders into the database.
Run once: cd trinker && python3 seed_builds.py
"""
import sys
sys.path.insert(0, ".")

from src.core.database import init_db
from src.build_orders.models import BuildOrder, BuildStep
from src.build_orders.manager import import_and_save, get_all_build_orders, delete_build_order

init_db()


def step(idx, desc, time_str="", pop=0, food=None, wood=None, gold=None, stone=None, age=None, notes=""):
    from src.build_orders.importer import _mmss_to_sec
    return BuildStep(
        index=idx, description=desc, time_str=time_str,
        time_sec=_mmss_to_sec(time_str) if time_str else 0,
        population=pop, food=food, wood=wood, gold=gold, stone=stone,
        age=age, notes=notes,
    )


BUILDS = []

# ─────────────────────────────────────────────────────────────────────────────
# 1. Standard 18 Vills Scout Rush (Any Civ)
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="18 Vills Scout Rush",
    civ="Any",
    strategy="Scout Rush",
    difficulty="Medium",
    author="Standard Meta",
    external_id="18-vills-scout-rush",
    source_url="https://www.buildorderguide.com",
    tags=["scout", "rush", "meta", "feudal"],
    notes="The most versatile opening in AoE2. 18 vills, 1 stable, 3–4 scouts harass enemy villagers. Aim for Feudal at ~9:30–10:00.",
    steps=[
        step(1,  "6 villagers → sheep (under TC)", "0:00", 4, notes="Queue villagers non-stop from TC"),
        step(2,  "7th vill → build house, then → sheep", "0:30", 7),
        step(3,  "8th–10th vill → sheep", "1:30", 10, notes="Move off sheep as they deplete"),
        step(4,  "11th vill → build Lumber Camp, then wood", "2:30", 11, wood=3),
        step(5,  "12th–14th vill → wood", "3:10", 14, wood=6),
        step(6,  "15th vill → build Mill → berries", "4:00", 15, notes="Lure 2nd boar before Mill fills"),
        step(7,  "16th–17th vill → berries (under Mill)", "4:30", 17),
        step(8,  "18th vill → farm under TC", "5:30", 18, food=6, wood=6),
        step(9,  "Research Double-Bit Axe when 200 wood", "6:00", 18, notes="Also research Horse Collar when wheat/food available"),
        step(10, "Click Feudal Age (use 500F / 800F → depends on timing, standard 800F+240G)", "7:00", 18,
             notes="500F/800F target. Send 2–3 vills to gold before clicking up"),
        step(11, "3 vills → build Barracks + Stable during Feudal transition", "7:00", 18,
             notes="Build Barracks first (Feudal requirement), then Stable"),
        step(12, "Queue 3–4 Scouts from Stable upon reaching Feudal (~9:30)", "9:30", 21,
             age="Feudal", notes="Send scouts to enemy base. Target vills on wood/gold"),
        step(13, "All new vills → gold (3–4) + remaining → farms", "9:30", 22,
             notes="Start Bloodlines + Stable upgrades when gold allows"),
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
# 2. 21 Pop Scout Rush
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="21 Pop Scout Rush",
    civ="Any",
    strategy="Scout Rush",
    difficulty="Medium",
    author="Standard Meta",
    external_id="21-pop-scout-rush",
    source_url="https://www.buildorderguide.com",
    tags=["scout", "rush", "feudal", "aggressive"],
    notes="More eco than 18-pop before attacking. 21 pop allows a smoother eco while still hitting Feudal at ~10:00.",
    steps=[
        step(1,  "6 vills → sheep", "0:00", 4, food=6),
        step(2,  "7th vill → house → sheep", "0:30", 7),
        step(3,  "8th–10th vill → sheep", "1:30", 10),
        step(4,  "11th vill → Lumber Camp → wood", "2:30", 11, wood=3),
        step(5,  "12th–14th vill → wood", "3:10", 14, wood=6),
        step(6,  "15th vill → Mill → berries", "4:00", 15),
        step(7,  "16th–18th vill → berries", "4:30", 18),
        step(8,  "19th–21st vill → gold (3 vills gold)", "5:30", 21, gold=3, notes="Prepare gold for Castle Age"),
        step(9,  "Click Feudal Age (~9:00–9:30)", "7:30", 21, notes="500F/800F standard"),
        step(10, "Build Barracks + Stable during Feudal up", "7:30", 21),
        step(11, "Reach Feudal. Queue 3 Scouts. Research Bloodlines.", "9:30", 23,
             age="Feudal", notes="Bloodlines is huge DPS increase; always research first"),
        step(12, "New vills → farms + gold. Click Castle at 800F/200G", "11:00", 25,
             notes="Aim for Castle at ~16:00"),
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
# 3. 22 Pop Archer Rush (Britons / Any)
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="22 Pop Archer Rush",
    civ="Any",
    strategy="Archer Rush",
    difficulty="Medium",
    author="Standard Meta",
    external_id="22-pop-archer-rush",
    source_url="https://www.buildorderguide.com",
    tags=["archer", "rush", "feudal", "meta"],
    notes="Classic Feudal archer aggression. Pump archers from 2 ranges, add fletching for 3-shot vills.",
    steps=[
        step(1,  "6 vills → sheep", "0:00", 4, food=6),
        step(2,  "7th vill → house → sheep", "0:30", 7),
        step(3,  "8th–10th vill → sheep", "1:30", 10),
        step(4,  "11th–13th vill → Lumber Camp → wood", "2:30", 13, wood=3),
        step(5,  "14th vill → Mill → berries", "3:30", 14),
        step(6,  "15th–17th vill → berries", "4:00", 17),
        step(7,  "18th–19th vill → gold", "5:00", 19, gold=2),
        step(8,  "20th–22nd vill → wood (bring wood to 6 total)", "5:30", 22, wood=6),
        step(9,  "Click Feudal Age at ~500F", "7:00", 22, notes="800F timing is also fine for slower Feudal"),
        step(10, "Build Barracks + Archery Range during Feudal up", "7:00", 22,
             notes="Send 2 vills to build both; Barracks needed for Feudal"),
        step(11, "Reach Feudal. Immediately start queueing Archers.", "9:30", 24,
             age="Feudal", notes="Keep 2–3 vills on gold for continuous arrow production"),
        step(12, "Research Fletching ASAP (3-shot vills)", "10:00", 25,
             notes="Archers become 3-shot on vills — huge power spike"),
        step(13, "Build 2nd Archery Range at 20 archers", "11:00", 27,
             notes="Add Double-Bit Axe + Horse Collar for eco"),
        step(14, "New vills → gold (5–6) + farms. Save for Castle at 800F/200G", "12:00", 29),
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
# 4. Men-at-Arms into Archers (M@A)
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="Men-at-Arms into Archers",
    civ="Any",
    strategy="Militia Rush",
    difficulty="Medium",
    author="Standard Meta",
    external_id="maa-into-archers",
    source_url="https://www.buildorderguide.com",
    tags=["maa", "archer", "rush", "militia", "feudal"],
    notes="Transition through M@A harassment to archers. Excellent against boom players and FC openers.",
    steps=[
        step(1,  "6 vills → sheep", "0:00", 4, food=6),
        step(2,  "7th vill → house → sheep", "0:30", 7),
        step(3,  "8th–10th vill → sheep", "1:30", 10),
        step(4,  "11th–13th vill → Lumber Camp → wood", "2:30", 13, wood=3),
        step(5,  "14th vill → Mill → berries", "3:30", 14),
        step(6,  "15th–17th vill → berries", "4:00", 17),
        step(7,  "18th–19th vill → gold (2 on gold)", "5:00", 19, gold=2),
        step(8,  "20th–22nd vill → wood", "5:30", 22, wood=5),
        step(9,  "At ~200G build Barracks. Click Feudal at ~4:30.", "4:30", 22,
             notes="Barracks before Feudal for M@A research"),
        step(10, "Research Man-at-Arms immediately upon reaching Feudal (140F/60G)", "9:30", 22,
             age="Feudal", notes="Queue 2–4 Militia immediately from Barracks"),
        step(11, "Build Archery Range. Start queueing Archers.", "9:30", 24),
        step(12, "Send M@A to enemy base. Harass vills at wood/gold.", "10:00", 25,
             notes="Focus on villagers, not military buildings"),
        step(13, "Research Fletching. Add 2nd Range at 15–20 archers.", "11:00", 28),
        step(14, "Click Castle at 800F/200G. Transition to archer-knight combo.", "14:00", 30),
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
# 5. Fast Castle into Knights
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="Fast Castle into Knights",
    civ="Any",
    strategy="Fast Castle",
    difficulty="Medium",
    author="Standard Meta",
    external_id="fast-castle-knights",
    source_url="https://www.buildorderguide.com",
    tags=["fast castle", "knight", "fc", "castle", "meta"],
    notes="Skip Feudal military and boom straight to Castle Age Knights. Feudal around 10–11 min, Castle at ~15–16 min.",
    steps=[
        step(1,  "6 vills → sheep", "0:00", 4, food=6),
        step(2,  "7th vill → house → sheep", "0:30", 7),
        step(3,  "8th–10th vill → sheep", "1:30", 10),
        step(4,  "11th–13th vill → Lumber Camp → wood", "2:30", 13, wood=3),
        step(5,  "14th vill → Mill → berries", "3:30", 14),
        step(6,  "15th–17th vill → berries", "4:00", 17),
        step(7,  "18th–21st vill → wood (bring wood to 7–8 total)", "5:00", 21, wood=8),
        step(8,  "22nd–25th vill → gold (4 on gold)", "6:00", 25, gold=4),
        step(9,  "Research Horse Collar + Double-Bit Axe", "6:30", 25),
        step(10, "Click Feudal Age at ~21–23 pop", "8:00", 25,
             notes="You want ~500F 800F — only build Barracks, no military"),
        step(11, "Build Barracks (required) during Feudal up. No military.", "8:00", 25),
        step(12, "Reach Feudal. Click Castle Age immediately (800F/200G)", "10:00", 26,
             age="Feudal", notes="Do NOT build an Archery Range or Stable — fast Castle only"),
        step(13, "During Castle up: build 2 Stables, send vills to gold (7+ on gold)", "10:00", 27,
             gold=7, notes="Add more farms during transition"),
        step(14, "Reach Castle. Queue 4–6 Knights from 2 Stables.", "15:30", 30,
             age="Castle", notes="Research Bloodlines + Forging ASAP"),
        step(15, "Add 3rd Stable. Begin adding Trebuchet support.", "17:00", 35,
             notes="Aim for 6+ Knights on field before Imperial"),
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
# 6. Economic Boom (Fast Castle → Boom)
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="Economic Boom",
    civ="Any",
    strategy="Boom",
    difficulty="Easy",
    author="Standard Meta",
    external_id="eco-boom-fc",
    source_url="https://www.buildorderguide.com",
    tags=["boom", "eco", "castle", "turtl"],
    notes="Safe eco-focused build. Reach Castle, build 2nd TC, then go crazy with villagers. Best on Arabia with a walled base.",
    steps=[
        step(1,  "6 vills → sheep", "0:00", 4, food=6),
        step(2,  "7th–10th vill → sheep / mill", "0:30", 10),
        step(3,  "11th–13th vill → wood", "2:30", 13, wood=3),
        step(4,  "14th–16th vill → berries", "3:30", 16),
        step(5,  "17th–22nd vill → gold (5 on gold)", "5:00", 22, gold=5),
        step(6,  "Research Horse Collar. Build more farms.", "6:00", 22),
        step(7,  "Click Feudal at ~800F (delayed, no rush)", "9:00", 22,
             notes="Build only Barracks as Feudal req. No mil spending."),
        step(8,  "Reach Feudal. Click Castle ASAP. Keep all vills on eco.", "11:00", 25,
             age="Feudal"),
        step(9,  "Build 2nd Town Center immediately upon Castle Age", "16:00", 30,
             age="Castle", notes="400 Wood 200 Stone. Place near extra resources."),
        step(10, "Build 3rd TC at ~35 pop. Research Wheelbarrow.", "18:00", 35,
             notes="Town Centers are your best investment"),
        step(11, "Boom to 60–70 vills. Imperial at ~25:00.", "20:00", 50),
        step(12, "In Imperial: build University, Chemistry, Siege Workshop.", "25:00", 70,
             age="Imperial", notes="Your massive eco advantage converts to military superiority"),
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
# 7. Drush + Fast Castle
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="Drush + Fast Castle",
    civ="Any",
    strategy="Fast Castle",
    difficulty="Hard",
    author="Standard Meta",
    external_id="drush-fc",
    source_url="https://www.buildorderguide.com",
    tags=["drush", "fast castle", "militia", "aggressive"],
    notes="Dark Age militia harass then fast castle. 3 militia disrupt enemy Feudal timing while you boom to Castle safely.",
    steps=[
        step(1,  "6 vills → sheep", "0:00", 4, food=6),
        step(2,  "7th vill → house → sheep", "0:30", 7),
        step(3,  "8th–10th vill → sheep", "1:30", 10),
        step(4,  "11th–12th vill → Lumber Camp → wood", "2:30", 12, wood=2),
        step(5,  "13th vill → gold (80G needed for Barracks soon)", "3:00", 13, gold=1),
        step(6,  "14th–16th vill → berries (Mill)", "3:30", 16),
        step(7,  "Build Barracks at ~2:30 with 2 wood vills temporarily", "3:30", 16,
             notes="Use 2 wood vills to build Barracks; send back after"),
        step(8,  "Queue 3 Militia. Drush leaves at ~5:30", "5:30", 16,
             notes="Head to enemy base immediately. Focus wood cutters."),
        step(9,  "17th–22nd vill → gold (5 gold total)", "5:30", 22, gold=5),
        step(10, "Send 3 Militia to enemy wood line or berries", "5:30", 16,
             notes="Kill 1 vill = offset cost. 2 kills = net positive. Dodge towers!"),
        step(11, "Click Feudal at ~22 pop", "8:30", 22,
             notes="Build ONLY a Barracks as Feudal req — you already have one"),
        step(12, "Reach Feudal. Click Castle immediately.", "10:30", 25, age="Feudal"),
        step(13, "Build 2 Stables during Castle up. Add farms.", "10:30", 26),
        step(14, "Reach Castle. Flood Knights.", "15:30", 30, age="Castle",
             notes="Drush buys time for this Castle timing to land hard"),
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
# 8. Mongol Scout Rush
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="Mongol Scout Rush",
    civ="Mongols",
    strategy="Scout Rush",
    difficulty="Medium",
    author="Standard Meta",
    external_id="mongol-scout-rush",
    source_url="https://www.buildorderguide.com",
    tags=["scout", "rush", "mongols", "feudal"],
    notes="Mongols get +30% Scout speed bonus in Feudal. Fastest scouts in the game — extremely hard to escape.",
    steps=[
        step(1,  "6 vills → sheep", "0:00", 4),
        step(2,  "7th vill → house → sheep", "0:30", 7),
        step(3,  "8th–10th vill → sheep", "1:30", 10),
        step(4,  "11th–13th vill → Lumber Camp → wood", "2:30", 13, wood=3),
        step(5,  "14th–15th vill → Mill → berries", "3:30", 15),
        step(6,  "16th–18th vill → berries", "4:30", 18),
        step(7,  "Click Feudal at ~500F / 18 pop", "7:00", 18,
             notes="Mongols get Feudal fast; aim for 9:30 Feudal"),
        step(8,  "Build Barracks + Stable during Feudal up (2 vills)", "7:00", 18),
        step(9,  "Reach Feudal. Queue Scouts. They are 30% faster!", "9:30", 21,
             age="Feudal", notes="Mongol scouts can dodge towers and outrun almost everything"),
        step(10, "3 vills → gold. Research Bloodlines.", "9:30", 22, gold=3),
        step(11, "Keep queueing scouts. 4–6 scouts = unstoppable harassment.", "10:00", 24,
             notes="Target enemy vills on berries or under construction buildings"),
        step(12, "New vills → farms + gold. Click Castle at 800F/200G.", "13:00", 28),
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
# 9. Britons Archer Rush
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="Britons Archer Rush",
    civ="Britons",
    strategy="Archer Rush",
    difficulty="Medium",
    author="Standard Meta",
    external_id="britons-archer-rush",
    source_url="https://www.buildorderguide.com",
    tags=["archer", "rush", "britons", "feudal", "meta"],
    notes="Britons Archery Ranges work 20% faster in Castle Age+. Stack archers in Feudal, dominate through Castle. Best archer civ.",
    steps=[
        step(1,  "6 vills → sheep", "0:00", 4, food=6),
        step(2,  "7th vill → house → sheep", "0:30", 7),
        step(3,  "8th–10th vill → sheep", "1:30", 10),
        step(4,  "11th–14th vill → Lumber Camp → wood", "2:30", 14, wood=4),
        step(5,  "15th vill → Mill → berries", "3:45", 15),
        step(6,  "16th–18th vill → berries", "4:30", 18),
        step(7,  "19th–21st vill → gold (3 on gold)", "5:30", 21, gold=3),
        step(8,  "22nd vill → wood. Double-Bit Axe when affordable.", "6:00", 22, wood=5),
        step(9,  "Click Feudal at ~500F / 22 pop", "7:30", 22,
             notes="Aim for 9:30–10:00 Feudal"),
        step(10, "Build Barracks + Archery Range. Archery Range first after Barracks.", "7:30", 22,
             notes="2 vills build; return to resource after"),
        step(11, "Reach Feudal. Start pumping Archers. Fletching ASAP.", "9:30", 24,
             age="Feudal", notes="Britons thumb ring + fletching = insane range"),
        step(12, "2nd Archery Range at 10–12 archers.", "11:00", 26,
             notes="Keep 4–5 vills on gold for 2 constant ranges"),
        step(13, "Click Castle at 800F/200G (after ~15 archers)", "13:00", 28),
        step(14, "Reach Castle. Britons ranges 20% faster → spam Crossbowmen.", "16:00", 32,
             age="Castle", notes="Research Bodkin Arrow for +1 range. Research Crossbow upgrade."),
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
# 10. Franks Fast Castle + Knights
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="Franks Fast Castle + Knights",
    civ="Franks",
    strategy="Fast Castle",
    difficulty="Medium",
    author="Standard Meta",
    external_id="franks-fc-knights",
    source_url="https://www.buildorderguide.com",
    tags=["fast castle", "knight", "franks", "castle", "meta"],
    notes="Franks get free Bloodlines and forager +15% bonus. Food-heavy Castle timing into insanely tanky Knights.",
    steps=[
        step(1,  "6 vills → sheep", "0:00", 4, food=6, notes="Franks foragers +15% food bonus"),
        step(2,  "7th–10th vill → sheep", "0:30", 10),
        step(3,  "11th–13th vill → wood (Lumber Camp)", "2:30", 13, wood=3),
        step(4,  "14th–16th vill → berries (Mill)", "3:30", 16,
             notes="Franks berries 15% faster — prioritize berries over farms early"),
        step(5,  "17th–18th vill → berries (8 total berries ideal)", "4:30", 18),
        step(6,  "19th–23rd vill → gold (4–5 on gold)", "5:30", 23, gold=4),
        step(7,  "Research Horse Collar early (cheap, big payoff)", "6:00", 23),
        step(8,  "Click Feudal ~800F / 23 pop. Build Barracks only.", "9:00", 23),
        step(9,  "Reach Feudal. Click Castle Age immediately.", "11:00", 25, age="Feudal",
             notes="Do not build Stable or Range — straight to Castle"),
        step(10, "Build 2 Stables + extra farms during Castle up", "11:00", 26,
             gold=6, notes="Bring gold to 6–7 vills"),
        step(11, "Reach Castle. Flood Knights — Franks have free Bloodlines!", "16:00", 30,
             age="Castle", notes="Franks: knights have +40 HP. Research Forging, Iron Casting ASAP"),
        step(12, "Add 3rd Stable. Destroy enemy with Knight mass.", "18:00", 35,
             notes="Frank knights at +40HP are among the tankiest in game"),
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
# 11. Mayan Archer Rush
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="Mayan Archer Rush",
    civ="Mayans",
    strategy="Archer Rush",
    difficulty="Medium",
    author="Standard Meta",
    external_id="mayan-archer-rush",
    source_url="https://www.buildorderguide.com",
    tags=["archer", "rush", "mayans", "feudal", "meta"],
    notes="Mayans start with extra resources (+1 food each vill). Mayans archers last 20% longer — extraordinary Feudal aggression.",
    steps=[
        step(1,  "7 vills → sheep (Mayans start with extra eagle, +1 food per vill bonus)", "0:00", 5,
             notes="Mayan bonus: each vill born with +1 food carried"),
        step(2,  "8th–10th vill → sheep", "0:30", 10),
        step(3,  "11th–14th vill → Lumber Camp → wood", "2:30", 14, wood=4),
        step(4,  "15th–17th vill → berries (Mill)", "3:30", 17),
        step(5,  "18th–20th vill → gold (3 on gold)", "5:00", 20, gold=3),
        step(6,  "21st–22nd vill → wood (6+ total wood)", "5:30", 22, wood=6),
        step(7,  "Click Feudal at ~22 pop / 500F", "7:00", 22),
        step(8,  "Build Barracks + 2x Archery Ranges during Feudal up", "7:00", 22,
             notes="Mayans can afford 2 ranges immediately"),
        step(9,  "Reach Feudal. Double Archery Range production immediately.", "9:30", 24,
             age="Feudal", notes="Mayan archers have +20% HP. Fletching first."),
        step(10, "5–6 vills on gold for 2 constant ranges.", "10:00", 26, gold=5),
        step(11, "Push with 8–10 archers. Mayan archers harder to kill.", "11:00", 28),
        step(12, "Click Castle at 800F/200G. Research El Dorado (Eagle Warriors +40HP).", "14:00", 30,
             age="Castle"),
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
# 12. Huns Fast Imperial
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="Huns Fast Imperial",
    civ="Huns",
    strategy="Fast Imperial",
    difficulty="Hard",
    author="Standard Meta",
    external_id="huns-fast-imperial",
    source_url="https://www.buildorderguide.com",
    tags=["fast imperial", "huns", "imperial", "aggressive"],
    notes="Huns need no houses (massive eco advantage). Fastest possible Imperial time. Target: Imperial at ~23–25 minutes.",
    steps=[
        step(1,  "6 vills → sheep (NO HOUSES NEEDED — Huns bonus)", "0:00", 4,
             notes="Never build houses as Huns! This saves huge wood"),
        step(2,  "7th–10th vill → sheep / lure boars", "0:30", 10, food=10),
        step(3,  "11th–14th vill → wood (Lumber Camp)", "2:30", 14, wood=4),
        step(4,  "15th–17th vill → berries (Mill)", "3:30", 17),
        step(5,  "18th–23rd vill → gold (5–6 on gold)", "5:00", 23, gold=5),
        step(6,  "All new vills → gold. Save wood for upgrades only.", "6:30", 25),
        step(7,  "Click Feudal at 26 pop (~800F). Build Barracks ONLY.", "9:00", 26),
        step(8,  "Reach Feudal. Click Castle immediately.", "11:00", 27, age="Feudal",
             notes="10+ vills on gold. No Feudal military."),
        step(9,  "Reach Castle. Click Imperial immediately (1000F/800G).", "16:00", 30,
             age="Castle", notes="During Castle: build 2 Stables or range (defensive), no wasted time"),
        step(10, "Build Stables + Siege Workshop upon Imperial.", "23:00", 45,
             age="Imperial", notes="Tarkan + Trebs or Paladin + Siege"),
        step(11, "Research all eco upgrades. Build battering rams. Push.", "25:00", 50),
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
# 13. Korean Tower Rush
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="Korean Tower Rush",
    civ="Koreans",
    strategy="Tower Rush",
    difficulty="Hard",
    author="Standard Meta",
    external_id="korean-tower-rush",
    source_url="https://www.buildorderguide.com",
    tags=["tower rush", "koreans", "feudal", "aggressive"],
    notes="Koreans: towers cheaper (stone) + +1 range. Sneak vills to enemy base in Dark Age and tower their resources.",
    steps=[
        step(1,  "6 vills → sheep", "0:00", 4, food=6),
        step(2,  "7th–9th vill → sheep", "0:30", 9),
        step(3,  "10th–12th vill → Lumber Camp → wood", "2:00", 12, wood=3),
        step(4,  "13th–15th vill → stone (Koreans: towers need stone, cheaper by 25%)", "3:00", 15,
             stone=3, notes="Korean towers cost 125 stone instead of 150"),
        step(5,  "16th–17th vill → berries (Mill)", "4:00", 17),
        step(6,  "Send 3–4 vills to enemy base at ~5:30 (before Feudal)", "5:30", 17,
             notes="Walk slowly, avoid scouts. Target wood line or gold mine."),
        step(7,  "Click Feudal at ~500F. Remaining vills: berries/wood.", "7:00", 17),
        step(8,  "Reach Feudal. Send building vills from step 6 to build towers.", "9:00", 19,
             age="Feudal", notes="Build Watch Tower next to their wood line or gold"),
        step(9,  "Korean Watch Tower has +1 range over normal. Extra deadly.", "9:30", 20,
             notes="Garrison archers if you have them for massive DPS"),
        step(10, "Build 2nd tower near their TC. Force them to fight or die.", "10:00", 21,
             notes="Attack eco, not units. Korean towers are amazing at this"),
        step(11, "Back home: click Castle. Build range/stable for defense.", "10:30", 23),
        step(12, "Reach Castle. Research Architecture → Towers become Bombard-ready.", "16:00", 28,
             age="Castle"),
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
# 14. Fast Castle Boom (Arabia Safe)
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="Fast Castle Boom (Walled Arabia)",
    civ="Any",
    strategy="Boom",
    difficulty="Easy",
    author="Standard Meta",
    external_id="fc-boom-arabia",
    source_url="https://www.buildorderguide.com",
    tags=["boom", "fast castle", "eco", "safe", "2tc"],
    notes="Wall up in Feudal, fast castle, then immediately drop 2nd TC. Best when opponent doesn't attack early.",
    steps=[
        step(1,  "6 vills → sheep", "0:00", 4, food=6),
        step(2,  "7th–10th vill → sheep", "0:30", 10),
        step(3,  "11th–13th vill → Lumber Camp → wood", "2:30", 13, wood=3),
        step(4,  "14th–16th vill → berries (Mill)", "3:30", 16),
        step(5,  "17th–20th vill → wood (wall building starts ~4:30)", "4:30", 20, wood=7,
             notes="Use 1 vill to pre-wall stone walls or palisades on gaps"),
        step(6,  "21st–23rd vill → gold (3 on gold)", "6:00", 23, gold=3),
        step(7,  "Research Horse Collar + Double-Bit Axe", "6:30", 23),
        step(8,  "Click Feudal at ~23 pop. Build Barracks only.", "9:00", 23),
        step(9,  "Reach Feudal. Finish walling. Click Castle ASAP.", "11:00", 25, age="Feudal",
             notes="Walling priority: stone wall the 2–3 main gap entrances"),
        step(10, "Reach Castle. Drop 2nd TC near new resources.", "16:00", 30,
             age="Castle", notes="400 wood 200 stone — place near secondary gold/stone"),
        step(11, "Produce vills from both TCs. Research Wheelbarrow.", "16:30", 30),
        step(12, "3rd TC at 45 pop. Imperial at 24–26 min.", "20:00", 45),
    ],
))

# ─────────────────────────────────────────────────────────────────────────────
# 15. Aztec Men-at-Arms Rush
# ─────────────────────────────────────────────────────────────────────────────
BUILDS.append(BuildOrder(
    name="Aztec Men-at-Arms Rush",
    civ="Aztecs",
    strategy="Militia Rush",
    difficulty="Medium",
    author="Standard Meta",
    external_id="aztec-maa-rush",
    source_url="https://www.buildorderguide.com",
    tags=["maa", "aztecs", "rush", "militia", "feudal", "meso"],
    notes="Aztec unique bonus: all military units +5 HP from start. Priests gain more HP per relic. Strong early militia rush.",
    steps=[
        step(1,  "6 vills → sheep (Aztecs start with extra resources)", "0:00", 4, food=6),
        step(2,  "7th–10th vill → sheep", "0:30", 10),
        step(3,  "11th–12th vill → Lumber Camp → wood", "2:30", 12, wood=2),
        step(4,  "13th vill → gold (need 75G for Barracks)", "3:00", 13, gold=1),
        step(5,  "14th–16th vill → berries (Mill)", "3:30", 16),
        step(6,  "Build Barracks at ~4:00 (float 200W)", "4:00", 16),
        step(7,  "17th–18th vill → gold (3 total gold)", "4:30", 18, gold=3),
        step(8,  "Queue 4 Militia. Send them together at ~5:30.", "5:30", 18,
             notes="Aztec militia have +5 HP — noticeably more durable"),
        step(9,  "19th–22nd vill → wood (6 total wood)", "5:30", 22, wood=6),
        step(10, "Click Feudal at ~22 pop. Research Man-at-Arms upgrade.", "7:30", 22,
             age="Feudal", notes="M@A research costs 140F/60G"),
        step(11, "Build Archery Range. Queue archers for follow-up.", "9:30", 24,
             age="Feudal"),
        step(12, "Push enemy base with 4 M@A. Aztec units are hard to kill.", "10:00", 24,
             notes="Combine M@A with archers for combo pressure"),
        step(13, "Click Castle at 800F/200G.", "14:00", 30),
        step(14, "Reach Castle. Research Eagle Warrior or Jaguar Warrior line.", "16:00", 32,
             age="Castle"),
    ],
))


# ─────────────────────────────────────────────────────────────────────────────
# Clear the dummy starter build, then save all 15
# ─────────────────────────────────────────────────────────────────────────────
existing = get_all_build_orders()
for bo in existing:
    if bo.external_id in (None, "", "spanish-scout-rush-18pop") or len(bo.steps) <= 5:
        delete_build_order(bo.id)
        print(f"Removed old build: '{bo.name}'")

saved = 0
for bo in BUILDS:
    result = import_and_save(bo)
    print(f"  [{saved+1:02d}] Saved: {result.name!r} ({len(result.steps)} steps) — {result.civ}")
    saved += 1

print(f"\nOK: {saved} build orders seeded into TRINKER database.")
print(f"  DB: {__import__('src.core.config', fromlist=['DB_PATH']).DB_PATH}")
