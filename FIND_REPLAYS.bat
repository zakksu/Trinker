@echo off
title TRINKER — Find AoE2 Replays
color 0E
cd /d "%~dp0"

echo.
echo  TRINKER will scan for your Age of Empires 2 replay folders
echo  (Documents, OneDrive, Steam savegame paths).
echo.

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR: Python required. Run INSTALL_WINDOWS.bat first.
    pause
    exit /b 1
)

python scripts\find_replays.py
echo.
pause
exit /b %ERRORLEVEL%
