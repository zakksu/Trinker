# TRINKER Hera Pro Coach

Train a **local Ollama coach** on Hera replay files — 1v1, team games, tournaments.

## What this actually does (honest scope)

| Layer | What happens | GPU fine-tune? |
|-------|----------------|----------------|
| **Replay scan** | Parses `.aoe2record` via mgz; finds matches where **Hera** is a player | No |
| **Corpus** | Aggregates feudal/castle/eAPM by civ → markdown in `%LOCALAPPDATA%\TRINKER\knowledge\hera\` | No |
| **RAG** | Coach prompts pull Hera corpus + existing AoE2 guides | No |
| **Ollama model** | `ollama create trinker-hera` from Modelfile (persona + corpus in SYSTEM prompt) | No |
| **Future LoRA** | True weight fine-tune on chat pairs from replays | Yes — separate pipeline |

**Bottom line:** TRINKER builds a **Hera-informed local coach** today without a GPU training cluster. It is not the same as training Llama weights on millions of tokens — but it is practical, private, and improves as you add replays.

---

## Quick start

1. **Install Ollama** — `SETUP_AI.bat`
2. **Add Hera replays** to:
   - `data/pro_replays/hera/` (in TRINKER folder)
   - `%LOCALAPPDATA%\TRINKER\corpus_inbox\`
3. **Build** — double-click `SETUP_HERA_COACH.bat`  
   Or: Settings → **Build Hera Coach**
4. **Use** — Model switches to `trinker-hera`; post-game coach + Dashboard Ask Coach use it.

---

## Where to get Hera replays

- [AoE2 Insights](https://aoe2insights.com/) — pro player replays
- Spectator saves from ranked / tournament games
- Team games: any rec where Hera is in the player list works

Your **own** 279 practice replays are scanned too — but Hera only appears in recs where she played.

---

## Commands

```bat
SETUP_HERA_COACH.bat
SETUP_HERA_COACH.bat --corpus-only
python scripts/build_hera_coach.py --folder "D:\HeraRecs" --max-files 200
```

---

## Future roadmap (RTS + app builder perspective)

### Near-term (high value, feasible in TRINKER)

1. **Multi-pro packs** — Viper, Liereyy, TheViper modelfiles from same pipeline  
2. **Embeddings RAG** — vector search over corpus chunks (better than keyword)  
3. **Build-order alignment** — match Hera feudal time to your BO step targets  
4. **Team game module** — pocket/flank role tags from map + player slot  
5. **Corpus auto-update** — rebuild when new files appear in `pro_replays/hera/`

### Medium-term (requires more parsing)

6. **Event timeline export** — vill count at feudal, first military, TC idle proxy  
7. **Synthetic Q&A pairs** — "Hera was late on feudal — what did she adjust?" for LoRA dataset  
8. **Cross-game pattern mining** — Arabia vs Arena timing clusters  
9. **Coach vs compare** — "You were 15s slower than Hera Britons avg on this map"

### Long-term (platform vision)

10. **LoRA fine-tune job** — export JSONL → Unsloth/Axolotl → import custom GGUF into Ollama  
11. **Live spectate coach** — observer stream → same pipeline as post-game  
12. **Community pro packs** — download "Tournament LC2024" corpus pack  
13. **Anti-hallucination guard** — coach must cite corpus stat or say "unknown"  
14. **Multi-language** — Hera corpus in EN; coach replies in player language  

### What I would *not* build first

- Full model training inside TRINKER UI (too heavy, wrong tool)  
- Cloud-only coach (conflicts with offline-first promise)  
- Memory reading / game injection (ToS risk)

---

## Architecture

```
.aoe2record (Hera in match)
    → mgz parser → ProGameRecord
    → aggregate by civ → hera_corpus.md
    → RAG chunks + Modelfile SYSTEM block
    → ollama create trinker-hera
    → postgame / chat uses settings.ollama_model
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 0 Hera games found | Add recs to `data/pro_replays/hera/` — your own games won't count unless Hera played |
| ollama create failed | Run `SETUP_AI.bat`, ensure llama3.2 pulled |
| Coach still generic | Check Settings → Model = `trinker-hera`, RAG enabled |
| Timings missing | DE patch mgz gap — corpus uses what parses |

See also: [`NORTH_STAR.md`](NORTH_STAR.md), [`CORPUS.md`](CORPUS.md).
