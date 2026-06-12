@echo off
title TRINKER — Sandbox (Fake Training Environment)
color 0B
cd /d "%~dp0"

echo.
echo  TRINKER SANDBOX — isolated fake data for testing
echo  Your real saves in %%LOCALAPPDATA%%\TRINKER are NOT used.
echo.

set TRINKER_SANDBOX=1

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  ERROR: Python required.
    pause
    exit /b 1
)

python scripts\seed_sandbox.py
if %ERRORLEVEL% NEQ 0 pause & exit /b %ERRORLEVEL%

python main.py
exit /b %ERRORLEVEL%
