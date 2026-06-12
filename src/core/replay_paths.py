"""
TRINKER - AoE2 DE replay folder discovery and access checks.

Finds real Documents / OneDrive / Steam savegame paths on Windows so TRINKER
can read .aoe2record files without manual path guessing.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .logger import logger

_STEAM_ID_RE = re.compile(r"^\d{17}$")
_AOE2_FOLDER_NAMES = (
    "Age of Empires 2 DE",
    "Age of Empires II DE",
    "AoE2DE",
)


@dataclass
class ReplayAccessReport:
    """Result of scanning the system for readable replay folders."""

    search_roots: list[Path] = field(default_factory=list)
    replay_count: int = 0
    newest_replay: str = ""
    readable: bool = False
    messages: list[str] = field(default_factory=list)


def _windows_documents() -> Path | None:
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        # CSIDL_PERSONAL = 5
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
            p = Path(buf.value)
            if p.exists():
                return p
    except Exception:
        pass
    return None


def _candidate_document_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()

    def add(p: Path | None) -> None:
        if not p:
            return
        try:
            resolved = str(p.expanduser().resolve())
        except OSError:
            resolved = str(p)
        if resolved not in seen:
            seen.add(resolved)
            roots.append(p)

    add(_windows_documents())
    add(Path.home() / "Documents")
    add(Path.home() / "OneDrive" / "Documents")
    add(Path.home() / "OneDrive")
    for env_key in ("USERPROFILE", "HOMEPATH"):
        raw = os.environ.get(env_key)
        if raw:
            add(Path(raw) / "Documents")

    return roots


def _aoe2_base_candidates() -> list[Path]:
    bases: list[Path] = []
    seen: set[str] = set()

    def add(p: Path) -> None:
        try:
            key = str(p.resolve())
        except OSError:
            key = str(p)
        if key not in seen:
            seen.add(key)
            bases.append(p)

    for doc in _candidate_document_roots():
        for name in _AOE2_FOLDER_NAMES:
            add(doc / "My Games" / name)

    add(Path.home() / "Games" / "Age of Empires 2 DE")
    add(Path.home() / "Games" / "Age of Empires II DE")

    if sys.platform == "win32":
        steam = _steam_install_path()
        if steam:
            add(steam / "steamapps" / "common" / "AoE2DE" / "savegame")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            packages = Path(local) / "Packages"
            if packages.is_dir():
                for pkg in packages.glob("Microsoft.MSPhoenix_*"):
                    add(pkg / "LocalCache" / "Local")
                    add(pkg / "LocalState")

    return bases


def _steam_install_path() -> Path | None:
    if sys.platform != "win32":
        return None
    try:
        import winreg

        keys = (
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam"),
        )
        for hive, sub in keys:
            try:
                with winreg.OpenKey(hive, sub) as key:
                    val, _ = winreg.QueryValueEx(key, "InstallPath")
                    p = Path(str(val))
                    if p.exists():
                        return p
            except OSError:
                continue
    except Exception:
        pass
    return None


def _expand_savegame_roots(base: Path) -> list[Path]:
    """Include Steam-ID savegame subfolders under an AoE2 DE root."""
    roots: list[Path] = []
    if not base.exists():
        return roots

    if base.name.lower() == "savegame" or any(
        base.glob("*.aoe2record")
    ):
        roots.append(base)

    try:
        if base.is_dir():
            roots.append(base)
            for child in base.iterdir():
                if child.is_dir() and _STEAM_ID_RE.match(child.name):
                    savegame = child / "savegame"
                    if savegame.is_dir():
                        roots.append(savegame)
                    else:
                        roots.append(child)
    except OSError as exc:
        logger.debug("Cannot list %s: %s", base, exc)

    return roots


def discover_replay_roots() -> list[Path]:
    """
    Return all folders that may contain .aoe2record files (newest-friendly order).
    Does not mutate settings.
    """
    found: list[Path] = []
    seen: set[str] = set()

    for base in _aoe2_base_candidates():
        for root in _expand_savegame_roots(base):
            try:
                key = str(root.resolve())
            except OSError:
                key = str(root)
            if key in seen or not root.exists():
                continue
            seen.add(key)
            found.append(root)

    return found


def count_replays_in(roots: list[Path]) -> tuple[int, str]:
    seen: set[str] = set()
    newest: Path | None = None
    newest_mtime = 0.0
    for root in roots:
        if not root.exists():
            continue
        try:
            for path in root.rglob("*.aoe2record"):
                try:
                    key = str(path.resolve())
                except OSError:
                    key = str(path)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    mtime = path.stat().st_mtime
                except OSError:
                    mtime = 0.0
                if mtime >= newest_mtime:
                    newest_mtime = mtime
                    newest = path
        except OSError as exc:
            logger.debug("Replay scan failed for %s: %s", root, exc)
    return len(seen), (newest.name if newest else "")


def probe_replay_access(extra_dirs: list[str] | None = None) -> ReplayAccessReport:
    """Scan configured + discovered paths and report whether replays are readable."""
    from .config import get_replay_search_dirs, settings

    report = ReplayAccessReport()
    roots: list[Path] = []

    for raw in extra_dirs or []:
        p = Path(raw)
        if p.exists():
            roots.extend(_expand_savegame_roots(p))

    for p in get_replay_search_dirs():
        if p not in roots:
            roots.append(p)

    for p in discover_replay_roots():
        if p not in roots:
            roots.append(p)

    report.search_roots = roots
    if not roots:
        report.messages.append(
            "No AoE2 replay folders found. Use Settings → Scan for Replays or Browse."
        )
        return report

    missing = [str(p) for p in roots if not p.exists()]
    if missing:
        report.messages.append(f"{len(missing)} configured folder(s) do not exist.")

    count, newest = count_replays_in([p for p in roots if p.exists()])
    report.replay_count = count
    report.newest_replay = newest
    report.readable = count > 0

    if count == 0:
        report.messages.append(
            "Folders found but no .aoe2record files yet — play a game or browse to your savegame folder."
        )
    else:
        report.messages.append(f"Found {count} replay(s). Newest: {newest or '—'}")

    if settings.replay_dirs:
        report.messages.append(f"Saved custom path(s): {len(settings.replay_dirs)}")

    return report


def ensure_replay_folders(*, save: bool = True) -> ReplayAccessReport:
    """
    Auto-discover AoE2 replay folders and persist new ones to settings.replay_dirs.
    Called at startup so TRINKER can access game files without manual setup.
    """
    from .config import settings

    discovered = discover_replay_roots()
    changed = False
    existing = {str(Path(p).resolve()) for p in settings.replay_dirs if p}

    for root in discovered:
        try:
            key = str(root.resolve())
        except OSError:
            key = str(root)
        if key not in existing:
            settings.replay_dirs.append(key)
            existing.add(key)
            changed = True
            logger.info("Registered replay folder: %s", root)

    if changed and save:
        settings.save()

    report = probe_replay_access()
    if report.readable:
        logger.info(
            "Replay access OK: %d file(s) across %d folder(s)",
            report.replay_count,
            len(report.search_roots),
        )
    else:
        logger.warning("Replay access: %s", "; ".join(report.messages) or "no replays")
    return report


def register_replay_folder(path: str | Path, *, save: bool = True) -> bool:
    """Add a user-selected folder (and savegame subfolders) to settings."""
    from .config import settings

    base = Path(path)
    if not base.exists():
        return False

    changed = False
    existing = {str(Path(p).resolve()) for p in settings.replay_dirs if p}
    for root in _expand_savegame_roots(base):
        try:
            key = str(root.resolve())
        except OSError:
            key = str(root)
        if key not in existing:
            settings.replay_dirs.append(key)
            existing.add(key)
            changed = True

    if changed and save:
        settings.save()
    return changed
