@echo off
title TRINKER — EXE Update and Launch
color 0B
cd /d "%~dp0"

echo.
echo  TRINKER — checking for EXE updates on GitHub...
echo.

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  Python is required for the auto-updater.
    echo  Launching existing TRINKER.exe without checking...
    goto :launch
)

python scripts\check_update.py --download
echo.

:launch
if exist "dist\TRINKER.exe" (
    echo  Starting TRINKER.exe...
    start "" "dist\TRINKER.exe"
) else (
    echo  ERROR: dist\TRINKER.exe not found.
    echo  Run BUILD_EXE.bat first, or use UPDATE_AND_RUN.bat for the Python version.
    pause
    exit /b 1
)
