@echo off
title TRINKER — Build Hera Pro Coach (Ollama)
color 0E
cd /d "%~dp0"

echo.
echo  ========================================
echo   TRINKER Hera Pro Coach Builder
echo  ========================================
echo.
echo  Scans replays where Hera appears and builds
echo  a custom Ollama model: trinker-hera
echo.
echo  Drop Hera .aoe2record files in:
echo    data\pro_replays\hera\
echo    or corpus_inbox (see Settings)
echo.

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR: Python required. Run INSTALL_WINDOWS.bat first.
    pause
    exit /b 1
)

python scripts\build_hera_coach.py %*
set ERR=%ERRORLEVEL%

echo.
if %ERR% EQU 0 (
    echo  Done. Launch TRINKER and use model trinker-hera in Settings.
) else (
    echo  Build incomplete — see messages above.
    echo  Run SETUP_AI.bat first if Ollama is not installed.
)
echo.
pause
exit /b %ERR%
