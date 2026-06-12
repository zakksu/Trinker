#!/usr/bin/env python3
"""
TRINKER release publisher — shows a confirmation popup, then push + tag + GitHub Release.

Usage:
    python scripts/release.py              # popup confirm, then release
    python scripts/release.py --yes        # skip popup (CI / agent)
    python scripts/release.py --no-push    # tag + GitHub only (already pushed)
    python scripts/release.py --with-exe   # attach dist/TRINKER.exe (must exist)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.config import GITHUB_REPO, get_app_version  # noqa: E402


def _confirm(title: str, message: str) -> bool:
    """Windows-friendly Yes/No popup; falls back to console prompt."""
    try:
        import ctypes

        MB_YESNO = 0x04
        IDYES = 6
        result = ctypes.windll.user32.MessageBoxW(0, message, title, MB_YESNO)
        return result == IDYES
    except Exception:
        pass
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        _app = QApplication.instance() or QApplication(sys.argv)
        box = QMessageBox()
        box.setWindowTitle(title)
        box.setText(message)
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        return box.exec() == QMessageBox.StandardButton.Yes
    except Exception:
        answer = input(f"{title}\n{message}\nRelease? [y/N]: ").strip().lower()
        return answer in ("y", "yes")


def _run(cmd: list[str], *, cwd: Path = ROOT) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def _github_token() -> str | None:
    import os

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    return None


def _release_notes(version: str) -> str:
    return f"""## TRINKER v{version}

See [commits](https://github.com/{GITHUB_REPO}/compare/v{version}...main) for full changelog.

### Quick start
- **Windows:** Download `TRINKER.exe` below, or clone and run `LAUNCHER.bat`
- **Updates:** `LAUNCHER.bat` checks GitHub and pulls the latest automatically
"""


def _create_github_release(
    tag: str,
    notes: str,
    exe_path: Path | None,
    token: str,
) -> str:
    import requests

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    api = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
    resp = requests.post(
        api,
        headers=headers,
        json={"tag_name": tag, "name": tag, "body": notes, "draft": False},
        timeout=30,
    )
    if resp.status_code == 422:
        # Release may exist — fetch latest for tag
        existing = requests.get(f"{api}/tags/{tag}", headers=headers, timeout=15)
        existing.raise_for_status()
        release = existing.json()
    else:
        resp.raise_for_status()
        release = resp.json()

    html_url = release.get("html_url", "")
    upload_url = release.get("upload_url", "").split("{")[0]

    if exe_path and exe_path.exists() and upload_url:
        with exe_path.open("rb") as fh:
            up = requests.post(
                f"{upload_url}?name=TRINKER.exe",
                headers={
                    **headers,
                    "Content-Type": "application/octet-stream",
                },
                data=fh,
                timeout=300,
            )
        up.raise_for_status()
        print(f"Uploaded: {exe_path.name}")

    return html_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish TRINKER release with confirmation")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation popup")
    parser.add_argument("--no-push", action="store_true", help="Skip git push (tag exists on remote)")
    parser.add_argument("--with-exe", action="store_true", help="Attach dist/TRINKER.exe")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest")
    args = parser.parse_args()

    version = get_app_version()
    tag = f"v{version}"
    exe = ROOT / "dist" / "TRINKER.exe"

    summary = (
        f"Publish TRINKER {tag} to GitHub?\n\n"
        f"Repo: {GITHUB_REPO}\n"
        f"Steps: {'skip push, ' if args.no_push else 'git push, '}git tag, GitHub Release"
        f"{', TRINKER.exe attach' if args.with_exe else ''}\n\n"
        f"Continue?"
    )

    if not args.yes and not _confirm("TRINKER Release", summary):
        print("Release cancelled.")
        return 0

    if not args.skip_tests:
        import os

        print("Running tests…")
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q"],
            cwd=ROOT,
            check=True,
            env=env,
        )

    if not args.no_push:
        _run(["git", "push", "origin", "main"])
        # Tag (create or move)
        exists = subprocess.run(
            ["git", "rev-parse", tag],
            cwd=ROOT,
            capture_output=True,
        )
        if exists.returncode != 0:
            _run(["git", "tag", "-a", tag, "-m", f"TRINKER {tag}"])
        _run(["git", "push", "origin", tag])

    token = _github_token()
    if not token:
        print("ERROR: No GitHub token. Set GITHUB_TOKEN or sign in via Git Credential Manager.")
        return 1

    notes = _release_notes(version)
    url = _create_github_release(
        tag,
        notes,
        exe if args.with_exe else None,
        token,
    )
    print(f"\nRelease published: {url}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Release failed: {exc}")
        sys.exit(1)
