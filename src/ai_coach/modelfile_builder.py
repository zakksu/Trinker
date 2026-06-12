"""
TRINKER - Ollama Modelfile builder for pro-player coach personas.

Creates a custom `trinker-hera` model via `ollama create` — specialized SYSTEM
prompt + base model (llama3.2). This is persona + knowledge injection, not LoRA.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..core.config import DATA_DIR, settings
from ..core.logger import logger
from .pro_replay_corpus import ProCorpusResult, build_knowledge_markdown


def modelfile_path(pro_key: str = "Hera") -> Path:
    d = DATA_DIR / "models"
    d.mkdir(parents=True, exist_ok=True)
    slug = pro_key.lower().replace(" ", "-")
    return d / f"trinker-{slug}.Modelfile"


def model_name(pro_key: str = "Hera") -> str:
    return f"trinker-{pro_key.lower().replace(' ', '-')}"


def build_modelfile_content(
    result: ProCorpusResult,
    *,
    base_model: str | None = None,
) -> str:
    base = base_model or settings.recommended_ollama_model or "llama3.2"
    pro = result.pro_name
    corpus_summary = build_knowledge_markdown(result)
    # Keep SYSTEM block under ~12k chars for Modelfile stability
    if len(corpus_summary) > 10000:
        corpus_summary = corpus_summary[:10000] + "\n\n[... corpus truncated ...]"

    system = f'''You are TRINKER Pro Coach — channeling {pro}'s Age of Empires II DE expertise.

You coach like an RTS improvement app mentor: specific, actionable, honest about data gaps.
You understand build orders, macro, scouting, army composition, and mental game.

Rules:
- Give 2-4 bullet points max unless asked for detail.
- Reference feudal/castle timing windows when relevant.
- Never invent replay stats — if unknown, say "play another game with overlay on."
- Compare the player to pro benchmarks when corpus data exists below.
- Team games: mention coordination, trade, map control.
- Tone: direct, encouraging, Hera-style clarity — no fluff.

## {pro} replay corpus (parsed from real games in TRINKER)

{corpus_summary}
'''

    return f"""FROM {base}

PARAMETER temperature 0.25
PARAMETER num_predict 900

SYSTEM \"\"\"
{system.strip()}
\"\"\"
"""


def write_modelfile(result: ProCorpusResult, *, base_model: str | None = None) -> Path:
    path = modelfile_path(result.pro_name)
    path.write_text(
        build_modelfile_content(result, base_model=base_model),
        encoding="utf-8",
    )
    logger.info("Wrote Modelfile: %s", path)
    return path


def create_ollama_model(
    result: ProCorpusResult,
    *,
    base_model: str | None = None,
    recreate: bool = True,
) -> tuple[bool, str]:
    """
    Run `ollama create trinker-hera -f Modelfile`.
    Returns (success, message).
    """
    import shutil

    if not shutil.which("ollama"):
        return False, "Ollama not installed — run SETUP_AI.bat first."

    mf = write_modelfile(result, base_model=base_model)
    name = model_name(result.pro_name)

    if recreate:
        subprocess.run(["ollama", "rm", name], capture_output=True, text=True)

    try:
        proc = subprocess.run(
            ["ollama", "create", name, "-f", str(mf)],
            capture_output=True,
            text=True,
            timeout=600,
            check=True,
        )
        msg = proc.stdout.strip() or f"Created model `{name}`"
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        return False, f"ollama create failed: {detail[:500]}"
    except subprocess.TimeoutExpired:
        return False, "ollama create timed out (10 min)."

    settings.ollama_model = name
    settings.pro_coach_model = name
    settings.pro_coach_player = result.pro_name
    settings.ai_coach_enabled = True
    settings.save()
    return True, msg


def full_pro_coach_build(
    pro_key: str = "Hera",
    *,
    max_files: int = 500,
    base_model: str | None = None,
    create_model: bool = True,
) -> tuple[ProCorpusResult, bool, str]:
    """Scan → corpus → optional ollama create. Returns (result, ok, message)."""
    from .pro_replay_corpus import build_pro_corpus

    result = build_pro_corpus(pro_key, max_files=max_files)
    if not create_model:
        write_modelfile(result, base_model=base_model)
        return result, True, f"Corpus built ({result.game_count()} games). Modelfile ready."

    ok, msg = create_ollama_model(result, base_model=base_model)
    if ok:
        msg = f"{result.game_count()} {pro_key} games → model `{model_name(pro_key)}`. {msg}"
    return result, ok, msg
