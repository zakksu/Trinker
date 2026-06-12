"""
TRINKER - Opt-in anonymous usage telemetry (local JSONL queue).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .config import DATA_DIR, settings
from .logger import logger

_TELEMETRY_FILE = DATA_DIR / "telemetry.jsonl"


def track(event: str, **props: Any) -> None:
    """Record an anonymous event when the user opted in."""
    if not settings.telemetry_opt_in:
        return
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **{k: v for k, v in props.items() if v is not None},
    }
    try:
        with _TELEMETRY_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=str) + "\n")
    except Exception as exc:
        logger.debug("telemetry write failed: %s", exc)
