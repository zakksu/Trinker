"""
TRINKER - Update checker for standalone TRINKER.exe via GitHub Releases.
Used by scripts/check_update.py before launching the packaged app.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .config import GITHUB_REPO, get_app_version
from .logger import logger

try:
    import requests as _requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

RELEASES_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
ASSET_NAME = "TRINKER.exe"


def _parse_version(version: str) -> tuple[int, ...]:
    """Convert '1.0.1' to (1, 0, 1) for comparison."""
    parts = re.findall(r"\d+", version)
    return tuple(int(p) for p in parts) if parts else (0,)


def is_newer(remote: str, local: str) -> bool:
    return _parse_version(remote) > _parse_version(local)


def fetch_latest_release() -> Optional[dict]:
    """Return GitHub latest release JSON, or None on failure."""
    if not _REQUESTS_OK:
        return None
    try:
        resp = _requests.get(
            RELEASES_LATEST,
            headers={"Accept": "application/vnd.github+json"},
            timeout=15,
        )
        if resp.status_code == 404:
            logger.info("No GitHub releases published yet.")
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("Could not check for updates: %s", exc)
        return None


def get_exe_download_url(release: dict) -> Optional[str]:
    for asset in release.get("assets", []):
        if asset.get("name") == ASSET_NAME:
            return asset.get("browser_download_url")
    return None


def check_for_update() -> dict:
    """
    Compare local VERSION to GitHub latest release.

    Returns dict with keys:
      local_version, remote_version, update_available, download_url, release_notes
    """
    local = get_app_version()
    result = {
        "local_version": local,
        "remote_version": None,
        "update_available": False,
        "download_url": None,
        "release_notes": "",
    }
    release = fetch_latest_release()
    if not release:
        return result

    remote_tag = (release.get("tag_name") or "").lstrip("v")
    result["remote_version"] = remote_tag
    result["release_notes"] = release.get("body") or ""
    result["download_url"] = get_exe_download_url(release)
    result["update_available"] = bool(
        remote_tag and is_newer(remote_tag, local) and result["download_url"]
    )
    return result


def download_exe_update(download_url: str, dest: Path) -> Path:
    """Download TRINKER.exe to dest (uses .part temp file). Returns final path."""
    if not _REQUESTS_OK:
        raise RuntimeError("requests is required for updates")

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".exe.part")
    logger.info("Downloading update from %s", download_url)

    with _requests.get(download_url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if chunk:
                    fh.write(chunk)

    if dest.exists():
        backup = dest.with_suffix(".exe.bak")
        dest.replace(backup)
    tmp.replace(dest)
    logger.info("Update saved to %s", dest)
    return dest
