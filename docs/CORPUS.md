# TRINKER Replay Corpus

CI and local dev use `tests/fixtures/replays/manifest.json` to regression-test replay parsing and postgame coaching.

## Local synthetic replays

The manifest can `"generate": true` entries — these create minimal binary fixtures (no real game data). They verify **no crash** and basic coach paths only.

## Adding real DE replays (recommended)

1. Play a game in AoE2 DE with overlay on.
2. Find the replay under `Documents/My Games/Age of Empires 2 DE/`.
3. Copy `.aoe2record` to `tests/fixtures/replays/your_name/`.
4. Add an entry to `manifest.json`:

```json
{
  "id": "real_arabia_win",
  "file": "your_name/MP Replay v101....aoe2record",
  "expect": {
    "analyze_no_crash": true,
    "engine_v2_quality_min": "low",
    "feudal_sec_min": 420,
    "feudal_sec_max": 1020
  }
}
```

5. Run: `python scripts/replay_corpus_test.py`

## Remote replays (optional)

For large files, host on GitHub Releases or a CDN and add to `"remote"`:

```json
"remote": [
  {
    "file": "remote/sample_mp.aoe2record",
    "url": "https://example.com/sample_mp.aoe2record",
    "sha256": "optional-hex-digest"
  }
]
```

`ensure_remote_files()` downloads missing files before tests run.

## What we assert today

| Check | Meaning |
|-------|---------|
| `analyze_no_crash` | Full import pipeline completes |
| `offline_coach_mentions_feudal` | Coach text references feudal when late |
| `engine_v2_quality_min` | Engine v2 quality ≥ threshold |
| `feudal_sec_min/max` | Extracted feudal within window |

Contributing 5–10 real replays (SP + MP, win + loss, multiple civs) is the **single highest-impact** contribution to TRINKER trust.

### Easy drop folder (no git required)

Copy `.aoe2record` files to:

```
%LOCALAPPDATA%\TRINKER\corpus_inbox\
```

TRINKER creates this folder on first run. Share those files with the developer or import via Practice tab.
