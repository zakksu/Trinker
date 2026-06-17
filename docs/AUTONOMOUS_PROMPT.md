# TRINKER — Autonomous Release Prompt (v4.0 → v9.0)

You are the TRINKER dev agent with FULL autonomy. Do not ask for permission to edit files, run tests, commit, push, or release. Stop only when milestones v4.0 through v9.0 are shipped to GitHub with TRINKER.exe attached on each release.

Repo: `c:\Users\godin\Desktop\TRINKER\trinker`  
GitHub: zakksu/Trinker  
Current version: 3.5.1 (exe on releases)  
Daily user entry: LAUNCHER.bat — you handle everything else.

Read first:

- `.cursor/rules/agent-autonomy.mdc`
- `.cursor/rules/release.mdc`
- `docs/NORTH_STAR.md`
- `src/build_orders/importer.py` (buildorderguide.com)
- `src/build_orders/step_enricher.py`

---

## OUT OF SCOPE (do not build)

- Training Arena / scored simulation scenarios / drill mini-games
- Plugin ecosystem / marketplace / third-party packs
- Version 10.0 milestone or "full loop complete" branding
- Fancy UI polish, Steam artwork, animations — functional only

---

## RESOURCE & TEST POLICY (match Arbitragem project)

Mirror `c:\Users\godin\Desktop\Arbitragem` settings:

ENV / config defaults:

```
RESOURCE_RAM_FRACTION=0.8
RESOURCE_GPU_FRACTION=0.4
RAM_BUDGET_MB=1200
LOW_RAM_MODE=false          # enable path for constrained hosts
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_PROBE_TIMEOUT_SECONDS=1.5
OLLAMA_ENABLED=true
TRINKER_BG_TESTS=1          # mirror ARBITRAGEM_BG_TESTS=1
```

Implement for TRINKER:

- `src/core/resource_profile.py` (or extend config.py) — same RAM/GPU fraction logic as Arbitragem `src/services/resource_profile.py`
- Ollama calls respect GPU fraction; batch/enrich jobs cap workers at ~80% RAM policy
- `scripts/test_worker.py` — background pytest every 5 min or on tests/ mtime change; writes `data/.dev/test_status.json`
- Wire into dev flow: spawn test worker during long build/import jobs; never block ship on full suite if fast subset passed
- `tests/conftest.py`: `OLLAMA_ENABLED=false` by default in tests; disable slow AI during bulk import tests

Tests: run full `python -m pytest tests/ -q` before each release; background worker runs fast subset continuously during dev.

---

## PRIORITY #1 — Native buildorderguide.com library (every install)

Every fresh TRINKER install must ship with the FULL buildorderguide.com catalog in SQLite — not 15 hand-seeded builds.

Build:

1. `scripts/sync_buildorderguide.py`
   - Crawl/discover all build URLs from buildorderguide.com (sitemap, civ index pages, pagination — be resilient)
   - Rate-limit politely (1 req/sec); cache raw HTML/json under `data/buildorderguide_cache/`
   - Import via existing `import_from_buildorderguide()` + `import_and_save()`
   - Store `external_id` = slug; upsert on re-sync (`updated_at`)
   - Progress log + resume on failure

2. Run `enrich_steps()` on every imported build — expand vague steps into micro-steps (house, boar, feudal click, vill assignments)

3. Optional Ollama pass (when enabled): add notes/hints per step using `RESOURCE_GPU_FRACTION`; cache results; skip in CI

4. Hook into:
   - `INSTALL_WINDOWS.bat` → sync if DB has < N builds or manifest stale
   - `init_db()` / first launch → background sync thread if missing
   - `UPGRADE_BUILDS.bat` → force full re-sync
   - Bundle a compressed snapshot in `data/bundled_builds.db` OR ship manifest + lazy download — prefer bundled DB so offline works

5. Tests:
   - `test_sync_buildorderguide.py` with mocked HTTP fixtures
   - assert `enrich_steps` increases step count on sample HTML
   - assert fresh `init_db` loads ≥50 builds (or bundled count)

Goal: Library tab shows hundreds of builds out of the box; overlay works on any of them.

---

## MILESTONE LADDER — ship each as a tagged release + TRINKER.exe

### v4.0 — Replay trust + auto-import

- Fix/patch mgz for DE v101 where possible; graceful degradation + quality score
- Auto-register replays on startup (extend `replay_paths.py`)
- Post-game card always appears within 30s of new `.aoe2record`
- Real replay fixtures in `tests/fixtures/replays/` + CI corpus
- Release: bump VERSION, agent_ship or `release.py --yes --with-exe`

### v5.0 — Adaptive overlay + personalized benchmarks

- Overlay shows YOUR median feudal vs build target (from session history)
- Step timing adjusts from your last 10 games on same build
- Dashboard KPI: personal benchmark row per civ/strategy
- No live OCR required for v5 — replay-derived personalization is enough

### v6.0 — Build intelligence (replaces Training Arena)

- Build-specific timing targets generated from BO steps + ideal_timings
- Compare tab: "you vs this build's pro band" per step
- Post-game: top 3 mistakes tied to build steps (rule-based, not LLM-only)
- Suggested next build from library based on worst timing axis

### v7.0 — Pro corpus + matchup-aware coach

- Expand pro_replay_corpus (Hera + others); bundled sample + user drop folder
- Coach cites benchmark + your history + pro timing for civ/matchup
- trinker-hera or llama3.2 via Ollama; RAG from `data/knowledge/`
- Hera coach build in `SETUP_HERA_COACH.bat` works end-to-end

### v8.0 — Team games + ranked polish

- Team game replay parsing where mgz allows
- aoe2.gg integration: import recent ranked when API available
- Honest ranked vs practice stats (extend `training_stats.py`)
- Multi-player compare in analytics

### v9.0 — Distribution complete

- One-click TRINKER.exe always on latest release (`UPDATE_EXE.bat` verified)
- INSTALL path: Python OR exe both get full build library
- Silent dependency check on launch
- README friend instructions: "download TRINKER.exe, double-click"
- No plugin system

---

## RELEASE WORKFLOW (each milestone)

1. Bump VERSION in VERSION file
2. `BUILD_EXE.bat` (PyInstaller) → `dist/TRINKER.exe`
3. `python -m pytest tests/ -q` (`QT_QPA_PLATFORM=offscreen`)
4. `git add -A` (exclude dist/, cache, secrets)
5. `git commit -m "Ship vX.Y: <one-line why>"`
6. `git push origin main`
7. `python scripts/release.py --yes --with-exe --skip-tests`
8. Verify https://github.com/zakksu/Trinker/releases/latest has TRINKER.exe asset

Use `TRINKER_SANDBOX=1` + `scripts/seed_sandbox.py` for dev — never touch user's real 279 replays.

---

## SUGGESTIONS TO INCLUDE (from north star, trimmed)

- Replay engine v3: quality enum, fallback parser, never crash on bad rec
- Post-game → adaptive drill SUGGESTION text only (no arena/simulation UI)
- Auto-import on folder watch (optional lightweight watcher)
- buildorderguide sync weekly check on LAUNCHER start
- Headless E2E smoke: `python main.py --smoke-test` exits 0
- `docs/FRIEND_INSTALL.md`: 3-step exe download guide

---

## DEFINITION OF DONE

You stop when:

- v4.0, v5.0, v6.0, v7.0, v8.0, v9.0 are tagged on GitHub
- Each release has TRINKER.exe attached
- Full buildorderguide library ships on fresh install
- Background test worker exists and runs
- `RESOURCE_RAM_FRACTION=0.8` and `RESOURCE_GPU_FRACTION=0.4` are implemented
- pytest suite green on final v9.0

Work continuously. Commit and release after each milestone. Do not wait for user approval.
