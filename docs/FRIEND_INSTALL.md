# Install TRINKER for a Friend (3 steps)

No Python, no git, no terminal — just download and play.

---

## Step 1 — Download

1. Open **[github.com/zakksu/Trinker/releases/latest](https://github.com/zakksu/Trinker/releases/latest)**
2. Under **Assets**, click **`TRINKER.exe`**
3. Save it anywhere (Desktop is fine)

---

## Step 2 — Run

Double-click **`TRINKER.exe`**.

First launch may take 10–20 seconds while Windows SmartScreen checks the file. Click **More info → Run anyway** if needed (the exe is built from the open-source repo).

---

## Step 3 — Play AoE2

1. Pick a build on **Start Here**
2. Turn on the **overlay** before your game
3. When you finish, TRINKER reads your replay and shows tips automatically

Your replays stay on your PC under `%LOCALAPPDATA%\TRINKER\`.

---

## Updates

- **Exe users:** download the latest `TRINKER.exe` from GitHub Releases again, or run **`UPDATE_EXE.bat`** if you cloned the repo.
- **Git users:** double-click **`LAUNCHER.bat`** — it pulls the latest version before starting.

---

## Optional: AI coach

For smarter post-game tips, install [Ollama](https://ollama.com) and run **`SETUP_AI.bat`** once. TRINKER works fully without it.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Exe won't start | Install [VC++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe) |
| No replays detected | Settings → Scan for replay folders |
| Overlay not visible | Press overlay hotkey (default Ctrl+Shift+O) |

Questions? Open an issue on GitHub: **zakksu/Trinker**
