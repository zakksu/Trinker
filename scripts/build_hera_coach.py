#!/usr/bin/env python3
"""
TRINKER — Build Hera (pro) coach from replay files.

Scans replays where Hera appears, writes RAG corpus, creates Ollama model `trinker-hera`.

Usage:
    python scripts/build_hera_coach.py
    python scripts/build_hera_coach.py --corpus-only
    python scripts/build_hera_coach.py --max-files 200 --pro Hera
    python scripts/build_hera_coach.py --folder "D:\\Replays\\Hera"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.ai_coach.modelfile_builder import full_pro_coach_build, model_name  # noqa: E402
from src.core.config import settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build TRINKER pro coach from replays")
    parser.add_argument("--pro", default="Hera", help="Pro player name to match")
    parser.add_argument("--max-files", type=int, default=500, help="Max pro games to extract")
    parser.add_argument("--base-model", default=None, help="Ollama base model (default llama3.2)")
    parser.add_argument(
        "--corpus-only",
        action="store_true",
        help="Build knowledge corpus only — skip ollama create",
    )
    parser.add_argument(
        "--folder",
        action="append",
        default=[],
        help="Extra folder to scan for replays (can repeat)",
    )
    args = parser.parse_args()

    print()
    print("=" * 56)
    print(f"  TRINKER Pro Coach Builder — {args.pro}")
    print("=" * 56)
    print()
    print("  Scans .aoe2record files where the pro appears in the match.")
    print("  Creates Ollama model via Modelfile (persona + corpus, not LoRA fine-tune).")
    print()

    extra = [Path(f) for f in args.folder if f]

    if extra:
        from src.ai_coach.pro_replay_corpus import build_pro_corpus, scan_pro_replays
        from src.ai_coach.modelfile_builder import create_ollama_model, write_modelfile

        result = scan_pro_replays(args.pro, max_files=args.max_files, extra_dirs=extra)
        from src.ai_coach.pro_replay_corpus import write_corpus

        write_corpus(result)
        if args.corpus_only:
            ok, msg = True, f"Corpus only: {result.game_count()} games."
        else:
            ok, msg = create_ollama_model(result, base_model=args.base_model)
    else:
        result, ok, msg = full_pro_coach_build(
            args.pro,
            max_files=args.max_files,
            base_model=args.base_model,
            create_model=not args.corpus_only,
        )

    print(f"  Scanned files: {result.scanned_files}")
    print(f"  {args.pro} games found: {result.game_count()}")
    if result.errors:
        print(f"  Parse warnings: {len(result.errors)}")
    print()
    if ok:
        print(f"  SUCCESS: {msg}")
        if not args.corpus_only:
            print(f"  Active model in TRINKER: {settings.ollama_model}")
            print(f"  Test in Settings → Test Connection, or Dashboard → Ask Coach.")
    else:
        print(f"  FAILED: {msg}")
        if result.game_count() == 0:
            print()
            print("  No pro replays found. Add files to:")
            print(f"    data/pro_replays/{args.pro.lower()}/")
            print("    %LOCALAPPDATA%\\TRINKER\\corpus_inbox\\")
            print("  Download Hera ranked/tournament recs from aoe2insights, etc.")
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
