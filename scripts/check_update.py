"""
Check GitHub Releases for a newer TRINKER.exe and download if available.
Called by UPDATE_EXE.bat before launching the packaged app.

Usage:
    python scripts/check_update.py [--download]
"""
import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.core.updater import check_for_update, download_exe_update


def main() -> int:
    parser = argparse.ArgumentParser(description="TRINKER.exe update checker")
    parser.add_argument(
        "--download", action="store_true",
        help="Download the latest TRINKER.exe if a newer release exists",
    )
    parser.add_argument(
        "--dest", default=str(_ROOT / "dist" / "TRINKER.exe"),
        help="Where to save the downloaded executable",
    )
    args = parser.parse_args()

    info = check_for_update()
    local = info["local_version"]
    remote = info["remote_version"] or "(no releases yet)"

    print(f"TRINKER version: {local}")
    print(f"Latest release:  {remote}")

    if not info["update_available"]:
        print("You are up to date (or no GitHub release with TRINKER.exe yet).")
        return 0

    print(f"Update available: v{local} -> v{info['remote_version']}")
    if args.download:
        dest = Path(args.dest)
        download_exe_update(info["download_url"], dest)
        print(f"Downloaded: {dest}")
    else:
        print("Run with --download to fetch the update.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
