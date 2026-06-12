"""
TRINKER - Pro player replay corpus builder (Hera and other pros).

Scans .aoe2record files, extracts stats when a named pro appears in the match,
and writes markdown knowledge for RAG + Ollama Modelfile generation.

Note: This is NOT full LLM fine-tuning — it builds a specialized knowledge base
and Ollama Modelfile persona. True LoRA fine-tuning is a separate future pipeline.
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..core.config import CORPUS_INBOX, DATA_DIR, settings
from ..core.logger import logger
from ..replay.mgz_parser import parse_with_mgz

# Default pro aliases (substring match, case-insensitive)
PRO_ALIASES: dict[str, list[str]] = {
    "Hera": ["hera", "hera_aoe", "hera aoe"],
}

_HERA_REPLAY_DIRS = (
    Path(__file__).resolve().parent.parent.parent / "data" / "pro_replays" / "hera",
    DATA_DIR / "pro_replays" / "hera",
    CORPUS_INBOX,
)


@dataclass
class ProGameRecord:
    replay_file: str
    replay_path: str
    player_name: str
    civ: str
    map_name: str = ""
    game_mode: str = "unknown"
    feudal_time_sec: int | None = None
    castle_time_sec: int | None = None
    imperial_time_sec: int | None = None
    eapm: float | None = None
    villager_high: int | None = None
    winner: bool | None = None
    duration_sec: int | None = None
    data_quality: str = "unknown"

    def summary_line(self) -> str:
        parts = [self.civ]
        if self.feudal_time_sec:
            parts.append(f"Feudal {_mmss(self.feudal_time_sec)}")
        if self.castle_time_sec:
            parts.append(f"Castle {_mmss(self.castle_time_sec)}")
        if self.eapm:
            parts.append(f"eAPM {self.eapm:.0f}")
        res = "WIN" if self.winner is True else "LOSS" if self.winner is False else "—"
        parts.append(res)
        return f"- `{self.replay_file[:48]}` — {' · '.join(parts)}"


@dataclass
class ProCorpusResult:
    pro_name: str
    games: list[ProGameRecord] = field(default_factory=list)
    scanned_files: int = 0
    errors: list[str] = field(default_factory=list)
    knowledge_dir: Path = field(default_factory=lambda: DATA_DIR / "knowledge" / "hera")
    manifest_path: Path = field(default_factory=lambda: DATA_DIR / "knowledge" / "hera" / "manifest.json")

    def game_count(self) -> int:
        return len(self.games)


def _mmss(sec: int) -> str:
    return f"{sec // 60}:{sec % 60:02d}"


def _name_matches_pro(player_name: str, pro_key: str) -> bool:
    if not player_name:
        return False
    low = player_name.lower().strip()
    aliases = PRO_ALIASES.get(pro_key, [pro_key.lower()])
    for alias in aliases:
        alias = alias.lower()
        if alias == low or alias in low:
            if alias == "hera" and "herald" in low:
                continue
            return True
    return False


def _find_pro_player(mgz, pro_key: str):
    for p in mgz.players:
        if _name_matches_pro(p.name, pro_key):
            return p
    return None


def _record_from_player(path: Path, player, mgz, pro_key: str) -> ProGameRecord:
    from ..replay.analyzer import _parse_filename_metadata

    meta = _parse_filename_metadata(path)
    return ProGameRecord(
        replay_file=path.name,
        replay_path=str(path.resolve()),
        player_name=player.name,
        civ=player.civ or "Unknown",
        map_name=mgz.map_name or "",
        game_mode="mp" if meta.get("is_mp") else "sp",
        feudal_time_sec=player.feudal_time_sec,
        castle_time_sec=player.castle_time_sec,
        imperial_time_sec=player.imperial_time_sec,
        eapm=player.eapm,
        villager_high=player.villager_high,
        winner=player.winner,
        duration_sec=mgz.duration_sec or None,
        data_quality="high" if player.feudal_time_sec else "low",
    )


def _pro_search_paths(extra: list[Path] | None = None) -> list[Path]:
    from ..core.config import get_replay_search_dirs

    paths: list[Path] = []
    seen: set[str] = set()
    for p in list(_HERA_REPLAY_DIRS) + list(extra or []) + get_replay_search_dirs():
        if not p.exists():
            continue
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            paths.append(p)
    return paths


def scan_pro_replays(
    pro_key: str = "Hera",
    *,
    max_files: int = 500,
    extra_dirs: list[Path] | None = None,
) -> ProCorpusResult:
    """
    Scan replay folders for games where the pro player appears (any slot).
    Parses mgz when available; skips files without a pro match.
    """
    result = ProCorpusResult(pro_name=pro_key)
    result.knowledge_dir = DATA_DIR / "knowledge" / pro_key.lower()
    result.manifest_path = result.knowledge_dir / "manifest.json"

    files: list[Path] = []
    for root in _pro_search_paths(extra_dirs):
        try:
            files.extend(root.rglob("*.aoe2record"))
        except OSError as exc:
            result.errors.append(f"Cannot scan {root}: {exc}")

    files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    seen_paths: set[str] = set()

    for path in files[: max_files * 3]:  # scan extra; filter duplicates
        if len(result.games) >= max_files:
            break
        try:
            key = str(path.resolve())
        except OSError:
            continue
        if key in seen_paths:
            continue
        seen_paths.add(key)
        result.scanned_files += 1

        try:
            mgz = parse_with_mgz(path)
        except Exception as exc:
            result.errors.append(f"{path.name}: {exc}")
            continue

        if not mgz.success:
            continue

        player = _find_pro_player(mgz, pro_key)
        if not player:
            continue

        result.games.append(_record_from_player(path, player, mgz, pro_key))

    logger.info(
        "Pro corpus %s: %d games from %d files scanned",
        pro_key,
        len(result.games),
        result.scanned_files,
    )
    return result


def _aggregate_by_civ(games: list[ProGameRecord]) -> dict[str, list[ProGameRecord]]:
    by_civ: dict[str, list[ProGameRecord]] = {}
    for g in games:
        by_civ.setdefault(g.civ, []).append(g)
    return by_civ


def build_knowledge_markdown(result: ProCorpusResult) -> str:
    """Generate markdown corpus for RAG retrieval."""
    pro = result.pro_name
    games = result.games
    lines = [
        f"# {pro} Replay Corpus (TRINKER auto-generated)",
        "",
        f"Generated from {len(games)} parsed replays where **{pro}** appears in the match.",
        "Use these timings as pro reference points — not as exact build order steps.",
        "",
    ]

    if not games:
        lines.extend([
            "## No games found yet",
            "",
            f"Drop {pro} tournament or ranked replays into:",
            f"- `data/pro_replays/{pro.lower()}/` in the TRINKER folder",
            f"- `%LOCALAPPDATA%\\TRINKER\\corpus_inbox\\`",
            "",
            "Then run **Build Hera Coach** in Settings or `SETUP_HERA_COACH.bat`.",
        ])
        return "\n".join(lines)

    feudals = [g.feudal_time_sec for g in games if g.feudal_time_sec]
    wins = sum(1 for g in games if g.winner is True)
    losses = sum(1 for g in games if g.winner is False)
    eapms = [g.eapm for g in games if g.eapm]

    lines.append("## Overall")
    lines.append(f"- Games parsed: {len(games)}")
    if wins + losses:
        lines.append(f"- Record in corpus: {wins}W / {losses}L")
    if feudals:
        lines.append(f"- Avg Feudal: {_mmss(int(statistics.mean(feudals)))}")
        lines.append(f"- Best Feudal: {_mmss(min(feudals))}")
    if eapms:
        lines.append(f"- Avg eAPM: {statistics.mean(eapms):.1f}")
    lines.append("")

    lines.append(f"## {pro} coaching principles (RTS fundamentals)")
    lines.append(
        f"- {pro} prioritizes clean Dark Age: TC never idle, consistent feudal click timing."
    )
    lines.append("- Scout info drives drush/archer/scout decision — map resources matter.")
    lines.append("- Castle timing separates booms from all-ins; punish floating resources.")
    lines.append("- Team games: coordinate flush timing and trade/monks on arena.")
    lines.append("")

    by_civ = _aggregate_by_civ(games)
    lines.append("## Timings by civilization")
    for civ in sorted(by_civ.keys()):
        cg = by_civ[civ]
        fsec = [g.feudal_time_sec for g in cg if g.feudal_time_sec]
        csec = [g.castle_time_sec for g in cg if g.castle_time_sec]
        lines.append(f"### {civ} ({len(cg)} games)")
        if fsec:
            lines.append(
                f"- Feudal: avg {_mmss(int(statistics.mean(fsec)))}, "
                f"best {_mmss(min(fsec))}"
            )
        if csec:
            lines.append(
                f"- Castle: avg {_mmss(int(statistics.mean(csec)))}, "
                f"best {_mmss(min(csec))}"
            )
        for rec in cg[:5]:
            lines.append(rec.summary_line())
        lines.append("")

    lines.append("## Recent sample games")
    for rec in games[:15]:
        lines.append(rec.summary_line())

    return "\n".join(lines)


def write_corpus(result: ProCorpusResult) -> Path:
    """Write markdown + manifest to DATA_DIR/knowledge/<pro>/."""
    result.knowledge_dir.mkdir(parents=True, exist_ok=True)
    md_path = result.knowledge_dir / f"{result.pro_name.lower()}_corpus.md"
    md_path.write_text(build_knowledge_markdown(result), encoding="utf-8")

    manifest = {
        "pro_name": result.pro_name,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "game_count": len(result.games),
        "scanned_files": result.scanned_files,
        "games": [asdict(g) for g in result.games[:200]],
    }
    result.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    from .rag import clear_cache

    clear_cache()
    logger.info("Wrote pro corpus: %s (%d games)", md_path, len(result.games))
    return md_path


def build_pro_corpus(
    pro_key: str = "Hera",
    *,
    max_files: int = 500,
    extra_dirs: list[Path] | None = None,
) -> ProCorpusResult:
    """Scan replays and write knowledge files."""
    result = scan_pro_replays(pro_key, max_files=max_files, extra_dirs=extra_dirs)
    write_corpus(result)
    settings.pro_corpus_built_at = datetime.now(timezone.utc).isoformat()
    settings.pro_corpus_game_count = len(result.games)
    settings.save()
    return result
