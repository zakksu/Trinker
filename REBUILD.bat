@echo off
title TRINKER 2.0 - Rebuild Data
cd /d "%~dp0"
echo.
echo  TRINKER 2.0 - Rebuilding your session data...
echo  (Purges bad imports, re-imports multiplayer replays)
echo.
python scripts\rebuild_data.py
echo.
echo  Done. Press any key to close, then run LAUNCHER.bat
pause >nul
