@echo off
title TRINKER — Publish Release
cd /d "%~dp0"
echo.
echo  TRINKER Release Publisher
echo  A confirmation popup will appear before anything is published.
echo.
python scripts\release.py %*
if %ERRORLEVEL% NEQ 0 pause
