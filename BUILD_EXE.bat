@echo off
title TRINKER — Build Standalone EXE
color 0B
echo.
echo  Building TRINKER standalone executable...
echo  This may take 3-10 minutes on first run.
echo.

cd /d "%~dp0"

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo [1/3] Installing build dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt pyinstaller --quiet
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo [2/3] Seeding build orders...
python seed_builds.py

echo [3/3] Running PyInstaller...
python -m PyInstaller trinker.spec --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo  Build complete!
echo  Executable: dist\TRINKER.exe
echo.
pause
