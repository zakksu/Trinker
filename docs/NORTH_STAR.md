# TRINKER North Star — Path to 100% and Beyond

> **Where we are:** ~72% of the full platform vision (v3.3).  
> **What 100% means:** A player opens `LAUNCHER.bat`, plays AoE2, and TRINKER honestly tells them what happened, what to fix, and what to drill next — without cloud accounts, without guesswork, without breaking on the next DE patch.

This document is **opinionated** and **not timeline-bound**. It describes what is possible, what is worth building, and what order makes sense.

---

## The 100% Definition

| Pillar | 100% looks like |
|--------|-----------------|
| **Trust** | Replay timings and win/loss match what you remember ≥95% of the time on current DE |
| **Loop** | Pick build → overlay in game → auto-import → compare → drill → repeat, zero manual steps |
| **Coach** | Useful tips offline; AI adds depth when Ollama is on; never nags about connection |
| **Distribution** | One double-click on Windows; signed exe optional; updates with popup |
| **Discoverability** | README/screenshots sell it; GitHub Release is polished; community can add builds |

---

## Current Scorecard (~72%)

| Area | % | Notes |
|------|---|-------|
| Daily player UX | **93%** | Performance Hub, overlay, launcher, drills |
| Replay trust | **45%** | Engine v2 helps; DE v101 mgz gaps remain |
| Training loop | **78%** | Adaptive drills + badges added in 3.3 |
| AI coach | **70%** | Keyword RAG; embeddings not yet |
| Live game sync | **55%** | Pause hash yes; real game clock no |
| Distribution | **85%** | RELEASE.bat; unsigned exe |
| Ecosystem | **25%** | Plugin stub; no marketplace |

---

## Phase A — Replay Trust (biggest lever to 85%)

**Problem:** If feudal time or win/loss is wrong, everything downstream (compare, coach, drills) loses trust.

### A1. Real DE replay corpus (high priority)
- Add 5–10 **real** `.aoe2record` files to `tests/fixtures/replays/` (or remote URLs in manifest)
- CI asserts: engine v2 quality ≥ medium, feudal within known range, no crash
- See `docs/CORPUS.md` for how to contribute replays

### A2. Event-level parsing (medium-hard)
- Extend `mgz_parser.py` beyond age-up achievements: vill count at feudal, military timeline
- Enables “you had 19 vills at click” coaching — huge for beginners
- **Possible:** Yes, with `mgz` library maintenance per DE patch

### A3. SP vs MP honesty (done in 3.3)
- `get_platform_stats()` splits training volume vs ranked win rate
- Win rate shows `—` until wins/losses exist; practice bar on charts
- **Next:** Manual result tag on Practice tab save; aoe2.gg import when API works

### A4. Remote corpus sync
- `manifest.json` `remote[]` downloads pinned replays on CI/dev setup
- Enables community replay packs without bloating git

---

## Phase B — Closed Training Loop (85% → 92%)

**Goal:** Every game automatically suggests the *next* focused practice step.

| Feature | Status | Next step |
|---------|--------|-----------|
| Pin drill + 3/3 progress | ✅ | — |
| Adaptive drill from postgame | ✅ 3.3 | Auto-pin option in Settings |
| Drill completion badges | ✅ 3.3 | Show on Steam-style profile card |
| Simulation scenarios | stub | Add 5 Arabia dark-age scenarios with scoring |
| Build-specific drills | not started | “Britons MAA: hit 21 pop by 4:30” generated from BO steps |
| LLM-generated custom drills | possible | One-shot Ollama prompt → ephemeral drill for this week |

**Opinion:** Rule-based adaptive drills get you 80% of the value. LLM drills are icing — use when Ollama is on, cache the good ones into the static catalog.

---

## Phase C — Live Game Intelligence (92% → 96%)

| Feature | Feasibility | Notes |
|---------|-------------|-------|
| Pause sync (screen hash) | ✅ Done | Works when clock region is stable |
| OCR resource panel | Medium | `easyocr` optional; needs region calibration UI |
| **Game clock OCR** | Hard but possible | Read MM:SS from HUD → sync overlay steps to *game time* not wall clock |
| macOS/Linux global hotkeys | Medium | `pynput` or platform-specific; test on Steam Deck |
| Memory reading | **Not recommended** | ToS risk; stay overlay-only |

**North star for live play:** Overlay step highlights when *in-game clock* crosses step target, not when you alt-tab to TRINKER.

---

## Phase D — AI Coach Depth (parallel track)

| Tier | What | Effort |
|------|------|--------|
| **Now** | Offline tips + keyword RAG (5 guides) | ✅ |
| **Next** | Embeddings RAG (local `chromadb` + `nomic-embed`) | 1–2 focused sessions |
| **Then** | Per-civ strategy packs (markdown → vector index) | Community content |
| **Moonshot** | Voice coach (TTS summary after game) | Fun, optional |
| **Moonshot** | “Watch my replay” multimodal (LLM + timeline JSON) | When event parsing exists |

**Opinion:** Embeddings RAG is the highest ROI AI upgrade. Voice is demo-ware unless quality is excellent.

---

## Phase E — Distribution & Trust (96% → 99%)

| Item | Path |
|------|------|
| Signed `TRINKER.exe` | Authenticode cert (~$200/yr) or self-sign + SmartScreen reputation |
| CI attaches exe to GitHub Release | Wire `release.py --with-exe` into workflow artifact promotion |
| Auto-update exe | `UPDATE_EXE.bat` already exists; polish delta updates later |
| macOS .app bundle | PyInstaller + notarization — possible for 4.x |
| Linux AppImage | Lower priority; Proton players exist |

---

## Phase F — Ecosystem & Discoverability (99% → 100%)

### F1. Discoverability (quick wins)
- Replace README placeholders with your Performance Hub + overlay screenshots
- 30-second GIF: pick build → overlay → postgame drill prompt
- GitHub social preview image (1280×640, gold banner)

### F2. Community build packs
- JSON pack format: `{ "pack_id", "builds": [...], "benchmarks": [...] }`
- Import from Settings → “Community Packs”
- Curated packs: “Hera Arabia 2026”, “Arena Meta”, “DM Noob Friendly”

### F3. Plugin system evolution
- **Today:** Drop `.py` in `data/plugins/`, hooks fire on session/replay/overlay
- **Tomorrow:** Plugin browser tab — list, enable, configure
- **Possible:** itch.io-style pack store (manual zip download, no payments needed initially)

### F4. Telemetry (opt-in cloud)
- Local JSONL today → optional anonymous aggregate sync
- “Global average feudal for Britons MAA” — powerful if privacy-preserving
- Requires backend (Supabase/Fly.io) — build only if user base justifies it

---

## Beyond 100% — What TRINKER Could Become

These are **not required** for 100%, but are genuinely possible for an AoE2 companion:

| Direction | Description |
|-----------|-------------|
| **Team training room** | Share build orders + drill assignments in a small group (LAN JSON sync) |
| **Tournament prep mode** | BO pool for a match format; random pick + timed prep |
| **Spectator coach** | Analyze live spectated game from recorded observer data |
| **Meta dashboard** | Pull pro match timings from open APIs when available |
| **Steam Workshop-style** | Skins for overlay (civ-themed palettes already started) |
| **Mobile companion** | Read-only stats PWA synced from desktop export |
| **Coaching marketplace** | Coaches publish drill packs; TRINKER hosts import only |

**Opinion:** Stay excellent at *one player's improvement loop* before becoming a platform. The overlay + replay + drill triangle is the moat.

---

## Recommended Build Order (no dates)

1. **Real replay corpus in CI** — unlocks trust for everything else  
2. **Game clock OCR sync** — biggest live-play UX jump  
3. **Embeddings RAG** — biggest AI quality jump  
4. **Signed exe + README screenshots** — biggest growth jump  
5. **Community build packs** — retention + sharing  
6. **Event-level mgz parsing** — pro-level insights  
7. **Plugin browser** — extensibility without core bloat  
8. **Telemetry server** — only if active user count warrants it  

---

## What You Should Do (non-coder)

| Goal | Action |
|------|--------|
| Daily play | `LAUNCHER.bat` only |
| Optional AI | `SETUP_AI.bat` once |
| Share TRINKER | Capture Performance Hub screenshot → GitHub / Discord |
| Help replay trust | Send 2–3 `.aoe2record` files (win + loss + SP) for the test corpus |
| Publish updates | `RELEASE.bat` → click Yes on popup |

---

## Related docs

- [`VISION_ROADMAP.md`](VISION_ROADMAP.md) — phase checklist with version milestones  
- [`CORPUS.md`](CORPUS.md) — how to add real replays for CI  
- [`README.md`](../README.md) — user-facing quick start  

---

*Last updated: TRINKER v3.3 — Performance Hub, adaptive drills, honest stats.*
