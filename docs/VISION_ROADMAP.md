# TRINKER — Path to 100% Platform Vision

Current estimate: **~72%** of full vision (after v3.3).  
Target: **100%** = one-click launcher + trusted data + closed training loop + distribution + discoverability.

**Full north-star roadmap (no timelines):** [`docs/NORTH_STAR.md`](NORTH_STAR.md)

---

## Phase 1 — One-click experience ✅ ~complete

| Item | Status |
|------|--------|
| LAUNCHER.bat = single entry point | ✅ |
| Update popup before git pull | ✅ |
| RELEASE.bat with popup before publish | ✅ |
| TRINKER.bat → LAUNCHER.bat | ✅ |
| Auto pip after update | ✅ |

**You do:** Double-click `LAUNCHER.bat` only.

---

## Phase 2 — Trusted replay data (target: 85%)

| Item | Status |
|------|--------|
| mgz parser with quality labels | partial |
| Replay engine v2 (multi-source merge) | ✅ |
| Pro benchmark DB (32 rows + JSON import) | ✅ |
| Honest training vs ranked stats | ✅ v3.3 |
| Real DE v101 replay corpus in CI | partial — see `docs/CORPUS.md` |
| Remote corpus download URLs | ✅ infra |
| Event-level timing reconstruction | not started |
| Clear “low quality” UX in Dashboard | ✅ Performance Hub |

---

## Phase 3 — Live game intelligence (target: 92%)

| Item | Status |
|------|--------|
| Windows global hotkeys | ✅ |
| Game pause sync (hash) | ✅ |
| OCR resource overlay | experimental |
| macOS/Linux global hotkeys | not started |
| Real game-clock sync | not started |

---

## Phase 4 — Training platform (target: 92%)

| Item | Status |
|------|--------|
| Drills + pin + progress 3/3 | ✅ |
| Adaptive drills from coach | ✅ v3.3 |
| Drill completion badges | ✅ v3.3 |
| Simulation stub | ✅ |
| Practice tab (advanced) | ✅ |
| LLM-generated custom drills | not started |

---

## Phase 5 — AI coach + distribution (target: 96%)

| Item | Status |
|------|--------|
| Ollama setup + RAG (5 guides) | ✅ |
| SETUP_AI.bat + launcher prompt | ✅ |
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

## Milestone targets (% vision)

| Version | Focus | ~% |
|---------|-------|-----|
| 3.2.0 | Performance Hub, engine v2, benchmarks | 65% |
| **3.3.0** | Honest stats, adaptive drills, badges | **72%** |
| 3.4 | Real replay corpus + clock OCR | 82% |
| 3.5 | Embeddings RAG + signed exe | 90% |
| 4.0 | Community packs + plugin browser | 96% |
| 4.1 | Screenshots, polish, telemetry opt-in | **100%** |

See [`docs/NORTH_STAR.md`](NORTH_STAR.md) for the full opinionated roadmap beyond 100%.
