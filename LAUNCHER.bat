@echo off
title TRINKER Launcher
cd /d "%~dp0"
python launcher.py
if %ERRORLEVEL% NEQ 0 (
    echo Launcher failed — falling back to direct start...
    call UPDATE_AND_RUN.bat
)
