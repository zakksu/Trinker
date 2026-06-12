# TRINKER — Path to 100% Platform Vision

Current estimate: **~58%** of full vision (after v3.1).  
Target: **100%** = one-click launcher + trusted data + closed training loop + distribution + discoverability.

---

## Phase 1 — One-click experience (target: 65%) ✅ in progress

| Item | Status |
|------|--------|
| LAUNCHER.bat = single entry point | ✅ |
| Update popup before git pull | ✅ |
| RELEASE.bat with popup before publish | ✅ |
| TRINKER.bat → LAUNCHER.bat | ✅ |
| Auto pip after update | ✅ |

**You do:** Double-click `LAUNCHER.bat` only.

---

## Phase 2 — Trusted replay data (target: 75%)

| Item | Status |
|------|--------|
| mgz parser with quality labels | partial |
| DE v101 replay corpus in CI | partial |
| Remote corpus download URLs | infra only |
| Event-level timing reconstruction | not started |
| Clear “low quality” UX in Dashboard | partial |

---

## Phase 3 — Live game intelligence (target: 82%)

| Item | Status |
|------|--------|
| Windows global hotkeys | ✅ |
| Game pause sync (hash) | ✅ |
| OCR resource overlay | experimental |
| macOS/Linux global hotkeys | not started |
| Real game-clock sync | not started |

---

## Phase 4 — Training platform (target: 90%)

| Item | Status |
|------|--------|
| Drills + pin + progress 3/3 | ✅ |
| Simulation stub | ✅ |
| Practice tab (advanced) | ✅ |
| Adaptive drills from coach/LLM | not started |
| Drill completion badges | not started |

---

## Phase 5 — AI coach + distribution (target: 95%)

| Item | Status |
|------|--------|
| Ollama setup + RAG (5 guides) | ✅ |
| Offline UX | ✅ |
| Embeddings RAG | not started |
| Signed TRINKER.exe releases | not started |
| RELEASE.bat auto-publish | ✅ |
| aoe2.gg reliability | blocked externally |

---

## Phase 6 — Discoverability + ecosystem (target: 100%)

| Item | Status |
|------|--------|
| README screenshots/GIFs | not started |
| GitHub social preview + topics | manual |
| Plugin marketplace / browser | not started |
| Community build packs | not started |
| Telemetry server (opt-in sync) | local only |

---

## Release workflow (for you + agent)

1. Agent finishes a version → commits → tells you **“Release ready”**
2. Double-click **`RELEASE.bat`** → **popup confirms** → push + tag + GitHub Release
3. You double-click **`LAUNCHER.bat`** → **popup if update** → latest TRINKER runs

Optional: `RELEASE.bat --with-exe` after `BUILD_EXE.bat` to attach `TRINKER.exe`.

---

## Milestone targets

| When | Version | % vision |
|------|---------|----------|
| Now | 3.1.1 | ~60% |
| +4 weeks | 3.2 | ~75% (replay trust) |
| +8 weeks | 3.3 | ~85% (live sync + drills) |
| +12 weeks | 4.0 | ~95% (signed exe + coach) |
| +16 weeks | 4.1 | **100%** (polish + discoverability) |
