@echo off
title TRINKER — Update and Launch
color 0B
cd /d "%~dp0"

echo.
echo  TRINKER — checking for updates...
echo.

REM ─── Python check ──────────────────────────────────────────────────────────
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR: Python is not installed or not in PATH.
    echo  Run INSTALL_WINDOWS.bat first.
    pause
    exit /b 1
)

REM ─── Git update (if this folder is a git clone) ────────────────────────────
git rev-parse --is-inside-work-tree >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo  [1/3] Pulling latest version from GitHub...
    git pull --ff-only
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo  WARNING: Could not pull updates automatically.
        echo  TRINKER will still launch with your current files.
        echo.
    ) else (
        echo  Updates applied.
    )
) else (
    echo  [1/3] Skipping git pull — folder is not a git repo yet.
    echo         See README_WINDOWS.txt for one-time GitHub setup.
)

REM ─── Dependencies (only if requirements changed) ───────────────────────────
echo  [2/3] Checking dependencies...
python -m pip install -r requirements.txt --quiet --disable-pip-version-check
if %ERRORLEVEL% NEQ 0 (
    echo  WARNING: Dependency check failed. Trying to launch anyway...
)

REM ─── Launch ────────────────────────────────────────────────────────────────
echo  [3/3] Starting TRINKER...
echo.
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  TRINKER exited with an error.
    echo  Log: %%LOCALAPPDATA%%\TRINKER\logs\trinker.log
    pause
)
