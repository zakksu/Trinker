@echo off
title TRINKER - Upgrade Build Orders
cd /d "%~dp0"
echo.
echo  Upgrading Britons Archer Rush + Fast Castle with detailed steps...
echo.
python scripts\upgrade_builds.py
echo.
echo  Done. Run LAUNCHER.bat and pick your build.
pause
