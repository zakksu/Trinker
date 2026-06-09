==================================================
  TRINKER — AoE2 Ultimate Training Companion
  Quick Start Guide (Windows)
==================================================

STEP 1 — First-time setup (run once):
  Double-click: INSTALL_WINDOWS.bat
  
  This will:
    • Check Python is installed
    • Install all required libraries
    • Seed 15 starter build orders into your library
    • Create a "TRINKER" shortcut on your Desktop

STEP 2 — Every time you want to launch TRINKER:
  Double-click: TRINKER.bat
  (or use the Desktop shortcut created in Step 1)

STEP 2b — Launch WITH automatic updates (recommended after GitHub setup):
  Double-click: UPDATE_AND_RUN.bat
  This pulls the latest code from GitHub, refreshes libraries if needed,
  then starts TRINKER. One click — no coding required.

--------------------------------------------------
REQUIREMENTS
--------------------------------------------------
• Python 3.11 or newer
  Download from: https://www.python.org/downloads/
  IMPORTANT: Tick "Add Python to PATH" during install

• Internet connection (first run only, to install libraries)

• Windows 10 or 11 recommended

--------------------------------------------------
CAN I PUT THIS FOLDER ANYWHERE?
--------------------------------------------------
YES. You can place this folder anywhere on your PC:
  C:\Games\TRINKER\
  D:\Tools\TRINKER\
  C:\Users\YourName\TRINKER\
  ... anywhere you like.

You can also rename the folder to anything you want.
The installer will always find the right location.

--------------------------------------------------
WHERE IS MY DATA?
--------------------------------------------------
Your build orders, sessions, and settings are stored in:
  C:\Users\YourName\AppData\Local\TRINKER\

This folder is separate from the app folder, so you
can move or update the app without losing your data.

--------------------------------------------------
GITHUB UPDATES (ONE-TIME SETUP)
--------------------------------------------------
Repo: https://github.com/zakksu/Trinker

After the first push (ask the AI assistant to do this), your daily workflow is:
  1. Double-click UPDATE_AND_RUN.bat
  2. TRINKER opens with the latest version

Your practice data stays on your PC at:
  C:\Users\YourName\AppData\Local\TRINKER\
  Updates never touch your saved sessions or settings.

--------------------------------------------------
BUILD STANDALONE EXE (OPTIONAL)
--------------------------------------------------
To create a double-clickable TRINKER.exe (no Python needed after build):
  Double-click: BUILD_EXE.bat
  Output: dist\TRINKER.exe

--------------------------------------------------
AI COACH (OPTIONAL)
--------------------------------------------------
For AI coaching features, install Ollama:
  https://ollama.ai
  
Then in TRINKER → Settings → AI Coaching, enable it
and click "Test Connection".

--------------------------------------------------
TROUBLESHOOTING
--------------------------------------------------
If TRINKER won't start:
  1. Make sure Python is installed and in PATH
  2. Run INSTALL_WINDOWS.bat again
  3. Check the log file:
     C:\Users\YourName\AppData\Local\TRINKER\logs\trinker.log

--------------------------------------------------
