@echo off
title TRINKER - Upgrade Build Orders
cd /d "%~dp0"
echo.
echo  Full buildorderguide.com re-sync + enrich steps...
echo.
python scripts\sync_buildorderguide.py --force
echo.
echo  Done. Run LAUNCHER.bat and pick your build.
pause
