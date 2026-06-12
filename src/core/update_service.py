"""
TRINKER - Unified update checks for launcher (git + GitHub Releases).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import get_app_version
from .logger import logger
from .updater import check_for_update, download_exe_update, is_newer


@dataclass
class UpdateStatus:
    local_version: str = ""
    git_available: bool = False
    git_behind: int = 0
    git_error: str = ""
    remote_version: Optional[str] = None
    exe_update_available: bool = False
    download_url: Optional[str] = None
    release_notes: str = ""
    messages: list[str] = field(default_factory=list)

    @property
    def has_git_update(self) -> bool:
        return self.git_behind > 0

    @property
    def has_any_update(self) -> bool:
        return self.has_git_update or self.exe_update_available

    def summary(self) -> str:
        lines = [f"Installed: v{self.local_version}"]
        if self.has_git_update:
            lines.append(f"Git: {self.git_behind} commit(s) behind origin/main")
        if self.exe_update_available and self.remote_version:
            lines.append(f"Release: v{self.remote_version} on GitHub (TRINKER.exe)")
        if not self.has_any_update:
            lines.append("You are on the latest version.")
        return "\n".join(lines)


def _run_git(args: list[str], root: Path, *, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def check_updates(root: Path | None = None) -> UpdateStatus:
    """Check git remote and GitHub Releases for updates."""
    root = root or Path(__file__).resolve().parent.parent.parent
    status = UpdateStatus(local_version=get_app_version())

    if (root / ".git").exists():
        status.git_available = True
        fetch = _run_git(["fetch", "origin", "--quiet"], root)
        if fetch.returncode != 0:
            status.git_error = (fetch.stderr or fetch.stdout or "git fetch failed").strip()
        else:
            behind = _run_git(["rev-list", "--count", "HEAD..origin/main"], root)
            if behind.returncode == 0 and behind.stdout.strip().isdigit():
                status.git_behind = int(behind.stdout.strip())

    release = check_for_update()
    status.remote_version = release.get("remote_version")
    status.exe_update_available = bool(release.get("update_available"))
    status.download_url = release.get("download_url")
    status.release_notes = release.get("release_notes") or ""

    if status.has_git_update:
        status.messages.append(f"Code update available ({status.git_behind} commits).")
    if status.exe_update_available and status.remote_version:
        if is_newer(status.remote_version, status.local_version):
            status.messages.append(f"TRINKER.exe v{status.remote_version} on GitHub.")
    return status


def apply_git_pull(root: Path | None = None) -> tuple[bool, str]:
    root = root or Path(__file__).resolve().parent.parent.parent
    if not (root / ".git").exists():
        return False, "Not a git repository."
    result = _run_git(["pull", "--ff-only", "origin", "main"], root)
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "git pull failed").strip()
        logger.warning("git pull failed: %s", err)
        return False, err
    return True, (result.stdout or "Updated from GitHub.").strip()


def apply_pip_install(root: Path | None = None) -> tuple[bool, str]:
    root = root or Path(__file__).resolve().parent.parent.parent
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        err = (result.stderr or "pip install failed").strip()
        return False, err
    return True, "Dependencies OK."


def download_latest_exe(dest: Path, download_url: str) -> Path:
    return download_exe_update(download_url, dest)
