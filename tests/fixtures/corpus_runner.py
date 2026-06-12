"""Replay corpus loader and coach/parser assertions (shared by pytest + script)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from tests.fixtures.synthetic_replay import build_synthetic_replay

MANIFEST_NAME = "manifest.json"


@dataclass
class CorpusResult:
    replay_id: str
    path: Path
    ok: bool
    detail: str = ""


def _manifest_path(base: Path) -> Path:
    return base / MANIFEST_NAME


def load_manifest(base: Path) -> dict:
    path = _manifest_path(base)
    if not path.exists():
        raise FileNotFoundError(f"Missing corpus manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_corpus_files(base: Path) -> list[Path]:
    """Generate or verify local replay files listed in manifest.json."""
    ensure_remote_files(base)
    manifest = load_manifest(base)
    paths: list[Path] = []
    for entry in manifest.get("replays", []):
        target = base / entry["file"]
        if entry.get("generate"):
            payload = build_synthetic_replay(
                feudal_sec=float(entry.get("feudal_sec", 480)),
                castle_sec=float(entry["castle_sec"]) if entry.get("castle_sec") else None,
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        if target.exists():
            paths.append(target)
    return paths


def ensure_remote_files(base: Path) -> None:
    """Download remote corpus entries when URL is listed in manifest."""
    import hashlib
    import urllib.request

    manifest = load_manifest(base)
    for entry in manifest.get("remote", []):
        url = entry.get("url")
        filename = entry.get("file")
        if not url or not filename:
            continue
        target = base / filename
        if target.exists() and not entry.get("sha256"):
            continue
        if target.exists() and entry.get("sha256"):
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            if digest == entry["sha256"]:
                continue
        target.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, target)
        if entry.get("sha256"):
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            if digest != entry["sha256"]:
                target.unlink(missing_ok=True)
                raise ValueError(f"SHA256 mismatch for {filename}")


def run_corpus_assertions(base: Path) -> list[CorpusResult]:
    """Run parser + offline coach checks for each manifest entry."""
    from unittest.mock import patch

    from src.ai_coach.postgame import run_postgame_coach
    from src.replay.analyzer import ReplayAnalysis, _parse_filename_metadata, analyze_replay

    manifest = load_manifest(base)
    ensure_corpus_files(base)
    results: list[CorpusResult] = []

    for entry in manifest.get("replays", []):
        rid = entry["id"]
        path = base / entry["file"]
        expect = entry.get("expect", {})
        if not path.exists():
            results.append(CorpusResult(rid, path, False, "file missing"))
            continue

        try:
            if expect.get("filename_is_mp"):
                meta = _parse_filename_metadata(path)
                if not meta.get("is_mp") and "MP Replay" not in path.name:
                    results.append(CorpusResult(rid, path, False, "expected MP filename metadata"))
                    continue

            analysis: ReplayAnalysis | None = None
            if expect.get("analyze_no_crash"):
                analysis = analyze_replay(path)
                if Path(analysis.replay_path).resolve() != path.resolve():
                    results.append(CorpusResult(rid, path, False, "analysis path mismatch"))
                    continue

            if expect.get("postgame_offline_alert") or expect.get("offline_coach_mentions_feudal"):
                with patch("src.ai_coach.postgame._is_ollama_available", return_value=False):
                    result = run_postgame_coach(str(path), civ="Britons", build_order_name="Test BO")
                if expect.get("postgame_offline_alert") and not result.overlay_alert:
                    results.append(CorpusResult(rid, path, False, "empty overlay alert"))
                    continue
                if expect.get("offline_coach_mentions_feudal"):
                    blob = (result.report + result.overlay_alert).lower()
                    has_feudal = "feudal" in blob or (
                        analysis and analysis.feudal_time_sec is not None
                    )
                    if not has_feudal:
                        results.append(
                            CorpusResult(rid, path, False, "offline coach missing feudal context")
                        )
                        continue

            results.append(CorpusResult(rid, path, True, "ok"))
        except Exception as exc:
            results.append(CorpusResult(rid, path, False, str(exc)))

    return results
