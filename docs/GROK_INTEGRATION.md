# Grok Build Agent — TRINKER Integration Guide

**Status:** Early beta (May 2026). No standalone REST “Grok Build Agent API” for third-party orchestration yet.  
**Recommended path for TRINKER dev:** CLI + headless mode + existing MCP/AGENTS.md compatibility.

---

## What exists today

| Surface | Available | Notes |
|---------|-----------|-------|
| **Grok Build CLI** | Yes (beta) | Terminal coding agent from xAI |
| **Subscription access** | SuperGrok / X Premium Plus | Not a plain xAI API key |
| **Headless mode** | `-p` flag | Script/CI automation |
| **MCP servers** | Supported | Same ecosystem as Cursor/Claude Code |
| **AGENTS.md / skills** | Supported | Repo conventions picked up automatically |
| **Direct model API** | `grok-code-fast-1` / `grok-build-0.1` | xAI API — pay-per-token, not full agent |
| **Dedicated Grok MCP for Cursor** | Not official yet | Use CLI hook or xAI API for now |

### Install (Windows)

```powershell
irm https://x.ai/cli/install.ps1 | iex
grok-build
```

Sign in with your SuperGrok / X Premium Plus account when prompted.

### Headless example (TRINKER repo)

```powershell
cd C:\Users\godin\Desktop\TRINKER\trinker
grok-build -p "Add a test for personal_benchmarks.py without changing unrelated files."
```

---

## TRINKER hook: `scripts/grok_agent.py`

Lightweight wrapper so agents/CI can invoke Grok Build when installed:

```powershell
python scripts/grok_agent.py "Summarize replay auto-import flow in src/replay/"
python scripts/grok_agent.py --plan "Design v10 overlay OCR fallback"
python scripts/grok_agent.py --check   # verify grok-build is on PATH
```

Behavior:

1. Looks for `grok-build` or `grok` on PATH.
2. Runs headless (`-p`) in the TRINKER repo root.
3. Exits non-zero if CLI missing (prints install URL).

---

## Cursor / MCP placeholder

Copy `.cursor/grok.example.json` → `.cursor/grok.json` and set your xAI API key if using the **model API** (not the full Grok Build agent):

```json
{
  "xai_api_key_env": "XAI_API_KEY",
  "default_model": "grok-code-fast-1",
  "notes": "Full Grok Build agent requires SuperGrok subscription CLI, not this key alone."
}
```

**Future:** When xAI ships an official Grok Build MCP server, add it to Cursor MCP settings the same way as other servers. Grok Build already reads existing MCP configs when run inside a repo.

---

## xAI console & API keys

1. [console.x.ai](https://console.x.ai) — create API key for **model** access (`grok-code-fast-1`).
2. Set `XAI_API_KEY` in your environment (never commit).
3. Grok **Build** CLI auth is separate — tied to X/SuperGrok subscription, not the console API key.

Pricing (API, approximate): ~$0.20/M input, ~$1.50/M output for `grok-code-fast-1` — suitable for scoped agent loops; full Grok Build beta is subscription-gated.

---

## When to use Grok vs Cursor

| Task | Tool |
|------|------|
| Daily TRINKER dev, releases, pytest | **Cursor agent** (this repo’s default) |
| Parallel subagent experiments | Grok Build (up to 8 subagents) |
| CI one-off codegen | `grok-build -p` via `scripts/grok_agent.py` |
| Production ship pipeline | `scripts/agent_ship.py` (unchanged) |

---

## Blockers / limitations

- **No public Grok Build REST API** — cannot replace Cursor MCP fully yet.
- **Beta stability** — plan mode required for large edits; review diffs carefully.
- **Subscription** — full agent needs SuperGrok/X Premium Plus, not just API credits.
- **SWE-bench gap** — trailing Claude/GPT on verified benchmarks; best for parallel exploration, not sole release gate.

---

## Quick checklist for TRINKER maintainers

- [ ] Install Grok Build CLI (`irm https://x.ai/cli/install.ps1 | iex`)
- [ ] Run `python scripts/grok_agent.py --check`
- [ ] Optional: set `XAI_API_KEY` for direct model calls
- [ ] Keep using `agent_ship.py` / `release.py --yes` for shipping
- [ ] Revisit this doc when xAI announces Grok Build MCP or public agent API
