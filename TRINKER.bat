@echo off
title TRINKER — AoE2 Training Companion
cd /d "%~dp0"
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo TRINKER exited with an error. Check the log file for details:
    echo %LOCALAPPDATA%\TRINKER\logs\trinker.log
    echo.
    pause
)
