@echo off
title TRINKER — AI Coach Setup (Ollama)
color 0E
cd /d "%~dp0"

echo.
echo  ========================================
echo   TRINKER AI Coach Setup
echo  ========================================
echo.
echo  This installs the local AI coach (optional).
echo  Session stats and tips work WITHOUT Ollama too.
echo.

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR: Python required. Run INSTALL_WINDOWS.bat first.
    pause
    exit /b 1
)

python scripts\setup_ollama.py --open-installer
set ERR=%ERRORLEVEL%

echo.
if %ERR% EQU 0 (
    echo  AI Coach is ready. Launch TRINKER with LAUNCHER.bat
) else (
    echo  Setup incomplete — TRINKER still works with offline tips.
    echo  Download Ollama manually: https://ollama.ai
)
echo.
pause
exit /b %ERR%
