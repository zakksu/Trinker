@echo off
title TRINKER Installer
color 0B
echo.
echo  ████████╗██████╗ ██╗███╗   ██╗██╗  ██╗███████╗██████╗
echo  ╚══██╔══╝██╔══██╗██║████╗  ██║██║ ██╔╝██╔════╝██╔══██╗
echo     ██║   ██████╔╝██║██╔██╗ ██║█████╔╝ █████╗  ██████╔╝
echo     ██║   ██╔══██╗██║██║╚██╗██║██╔═██╗ ██╔══╝  ██╔══██╗
echo     ██║   ██║  ██║██║██║ ╚████║██║  ██╗███████╗██║  ██║
echo     ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
echo.
echo  AoE2 Ultimate Training Companion — Installer
echo  ============================================
echo.

REM ─── Check Python ──────────────────────────────────────────────────────────
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Python is not installed or not in PATH.
    echo.
    echo  Please install Python 3.11+ from https://www.python.org/downloads/
    echo  Make sure to tick "Add Python to PATH" during install.
    echo.
    echo  Then run this installer again.
    echo.
    pause
    exit /b 1
)
python --version
echo  Python found OK.
echo.

REM ─── Install dependencies ──────────────────────────────────────────────────
echo [2/5] Installing dependencies (PySide6, requests, beautifulsoup4, matplotlib)...
echo  This may take 2-5 minutes on first run...
echo.
python -m pip install --upgrade pip --quiet
python -m pip install PySide6 requests beautifulsoup4 matplotlib mss --quiet
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Failed to install dependencies.
    echo  Check your internet connection and try again.
    echo.
    pause
    exit /b 1
)
echo  Dependencies installed OK.
echo.

REM ─── Seed build orders ─────────────────────────────────────────────────────
echo [3/5] Seeding build order library...
python seed_builds.py
if %ERRORLEVEL% NEQ 0 (
    echo  WARNING: Build order seeding failed. You can retry later with: python seed_builds.py
    echo.
)
echo [3b/5] Syncing buildorderguide.com catalog (if library is thin)...
python scripts\sync_buildorderguide.py --if-stale
if %ERRORLEVEL% NEQ 0 (
    echo  WARNING: buildorderguide sync skipped or partial. Retry: python scripts\sync_buildorderguide.py
    echo.
)
echo.

REM ─── Get install location ──────────────────────────────────────────────────
echo [4/5] Setting up launcher...

REM Figure out where this batch file lives — that's the TRINKER folder
set "TRINKER_DIR=%~dp0"
REM Remove trailing backslash
if "%TRINKER_DIR:~-1%"=="\" set "TRINKER_DIR=%TRINKER_DIR:~0,-1%"

echo  TRINKER is located at: %TRINKER_DIR%
echo.

REM ─── Create desktop shortcut ───────────────────────────────────────────────
echo [5/5] Creating desktop shortcut...

set "SHORTCUT=%USERPROFILE%\Desktop\TRINKER.bat"
(
    echo @echo off
    echo title TRINKER — AoE2 Training Companion
    echo cd /d "%TRINKER_DIR%"
    echo call LAUNCHER.bat
) > "%SHORTCUT%"

echo  Shortcut created: %SHORTCUT%
echo  (Uses LAUNCHER.bat — retro launcher with auto-update)
echo.

REM ─── Done ──────────────────────────────────────────────────────────────────
echo  ╔══════════════════════════════════════════════════════╗
echo  ║   TRINKER is ready!                                  ║
echo  ║                                                      ║
echo  ║   Double-click "TRINKER" on your Desktop to launch.  ║
echo  ║                                                      ║
echo  ║   You can also run: python main.py                   ║
echo  ║   from inside this folder at any time.               ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  Press any key to launch TRINKER now...
pause >nul

python main.py
