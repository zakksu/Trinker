#!/usr/bin/env python3
"""
Seed TRINKER sandbox — fake sessions, sample Hera corpus, synthetic replays.

Requires TRINKER_SANDBOX=1 (set by SANDBOX.bat).
Does NOT touch your real %LOCALAPPDATA%\\TRINKER\\ data.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("TRINKER_SANDBOX", "1")

from src.core.config import (  # noqa: E402
    CORPUS_INBOX,
    DATA_DIR,
    is_sandbox_mode,
)
from src.core.database import init_db  # noqa: E402


def _write_sample_hera_corpus() -> Path:
    hera_dir = DATA_DIR / "knowledge" / "hera"
    hera_dir.mkdir(parents=True, exist_ok=True)
    md = hera_dir / "hera_corpus.md"
    md.write_text(
        """# Hera Replay Corpus (TRINKER sandbox — synthetic)

Generated for fake training environment testing. Not real pro data.

## Overall
- Games parsed: 8 (synthetic)
- Avg Feudal: 9:05
- Best Feudal: 8:42

## Timings by civilization
### Britons (3 games)
- Feudal: avg 9:00, best 8:42
- `sandbox_hera_britons_1.aoe2record` — Britons · Feudal 8:42 · WIN

### Mayans (2 games)
- Feudal: avg 9:15, best 9:05

## Hera coaching principles (RTS fundamentals)
- Clean Dark Age TC queue — zero idle before loom decision.
- Scout pathing on Arabia determines drush vs range timing.
- Team games: coordinate flush with pocket trade if needed.
""",
        encoding="utf-8",
    )
    return md


def _ensure_build_orders() -> None:
    from src.build_orders.manager import get_all_build_orders, import_and_save
    from src.build_orders.models import BuildOrder, BuildStep

    if get_all_build_orders():
        return
    import_and_save(
        BuildOrder(
            name="[sandbox] Britons Archer Rush",
            civ="Britons",
            strategy="Archer Rush",
            difficulty="Medium",
            tags=["sandbox", "practice"],
            steps=[
                BuildStep(index=1, description="Queue 2 villagers", population=6),
                BuildStep(index=2, description="Build house", population=10),
            ],
        )
    )


def _seed_sessions() -> int:
    from src.analytics.session import Session, save_session
    from src.build_orders.manager import get_all_build_orders

    _ensure_build_orders()
    bos = get_all_build_orders()
    if not bos:
        return 0
    bo = bos[0]
    today = datetime.now(timezone.utc).date().isoformat()
    feudals = [555, 570, 600, 540, 620, 580, 595, 610]
    count = 0
    for i, feudal in enumerate(feudals):
        save_session(
            Session(
                build_order_id=bo.id,
                date=today,
                duration_sec=1800 + i * 60,
                feudal_time_sec=feudal,
                castle_time_sec=feudal + 360 if i % 2 == 0 else None,
                result="practice" if i % 3 else "win",
                accuracy_pct=55.0 + i * 3,
                notes=f"[sandbox] Fake session {i + 1} for Performance Hub charts",
                civ=bo.civ,
                game_mode="sp",
                data_quality="medium",
            )
        )
        count += 1
    return count


def _copy_synthetic_replays() -> int:
    from tests.fixtures.synthetic_replay import write_synthetic_mp_replay

    pro_dir = ROOT / "data" / "pro_replays" / "hera"
    pro_dir.mkdir(parents=True, exist_ok=True)
    inbox = CORPUS_INBOX
    inbox.mkdir(parents=True, exist_ok=True)
    n = 0
    for name, feudal in (
        ("sandbox_hera_britons_1.aoe2record", 522),
        ("sandbox_practice_1.aoe2record", 600),
    ):
        for dest in (pro_dir / name, inbox / name):
            write_synthetic_mp_replay(dest, feudal_sec=float(feudal))
            n += 1
    return n


def main() -> int:
    if not is_sandbox_mode():
        print("ERROR: Set TRINKER_SANDBOX=1 (use SANDBOX.bat)")
        return 1

    print()
    print("  TRINKER Sandbox Seed")
    print("  ====================")
    print(f"  Data dir: {DATA_DIR}")
    print()

    init_db()
    sessions = _seed_sessions()
    corpus = _write_sample_hera_corpus()
    replays = _copy_synthetic_replays()

    print(f"  Sessions seeded: {sessions}")
    print(f"  Hera corpus: {corpus}")
    print(f"  Synthetic replays: {replays // 2} files")
    print()
    print("  Launch with SANDBOX.bat to explore fake training data.")
    print("  Your real TRINKER data is untouched.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
