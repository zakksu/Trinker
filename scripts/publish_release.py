"""One-shot GitHub release publisher for TRINKER.exe."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.config import GITHUB_REPO, get_app_version

try:
    import requests
except ImportError:
    print("ERROR: requests not installed")
    sys.exit(1)


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


def main() -> int:
    version = get_app_version()
    tag = f"v{version}"
    exe = ROOT / "dist" / "TRINKER.exe"
    if not exe.exists():
        print(f"ERROR: Missing {exe} — run BUILD_EXE.bat first.")
        return 1

    token = _github_token()
    if not token:
        print("ERROR: No GitHub token. Set GITHUB_TOKEN or sign in via Git Credential Manager.")
        return 1

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    api = f"https://api.github.com/repos/{GITHUB_REPO}/releases"

    notes = """## TRINKER v2.0.0

### What's new
- **Start Here** workflow — pick a build, show overlay, play
- **Tabbed overlay** — Steps, Resources, Tips (smaller, always-on-top)
- **Auto-detect games** — SP, MP, and team games save to Analytics automatically
- **Overlay pause sync** — timer pauses when AoE2 is paused
- **Ollama auto-enable** — AI coach turns on when Ollama is running
- **Validated analytics pipeline** — cleaner session data (v2 DB)

### For new users
1. Download **TRINKER.exe** below
2. Double-click to run (no Python needed)
3. Optional: install [Ollama](https://ollama.ai) + `ollama pull llama3` for AI coaching

### Data location
Your sessions and settings stay in `%LOCALAPPDATA%\\TRINKER\\` — separate from the app.
"""

    # Delete existing release for this tag if re-publishing
    existing = requests.get(f"{api}/tags/{tag}", headers=headers, timeout=30)
    if existing.status_code == 200:
        rid = existing.json()["id"]
        requests.delete(f"{api}/{rid}", headers=headers, timeout=30)

    create = requests.post(
        api,
        headers=headers,
        json={
            "tag_name": tag,
            "name": f"TRINKER {tag}",
            "body": notes,
            "draft": False,
            "prerelease": False,
        },
        timeout=60,
    )
    if create.status_code not in (200, 201):
        print(f"ERROR: Create release failed ({create.status_code}): {create.text[:500]}")
        return 1

    release = create.json()
    upload_url = release["upload_url"].replace("{?name,label}", "")
    with exe.open("rb") as fh:
        up = requests.post(
            upload_url,
            headers={
                **headers,
                "Content-Type": "application/octet-stream",
            },
            params={"name": "TRINKER.exe"},
            data=fh,
            timeout=600,
        )
    if up.status_code not in (200, 201):
        print(f"ERROR: Upload failed ({up.status_code}): {up.text[:500]}")
        return 1

    url = release.get("html_url", "")
    print(f"OK: Published {tag}")
    print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
