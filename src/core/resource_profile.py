"""Hardware-aware resource tuning for constrained hosts (<16 GB RAM).

Mirrors Arbitragem resource policy: cap workers and caches from RAM/GPU fractions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

RESOURCE_RAM_FRACTION = float(os.environ.get("RESOURCE_RAM_FRACTION", "0.8"))
RESOURCE_GPU_FRACTION = float(os.environ.get("RESOURCE_GPU_FRACTION", "0.4"))
RAM_BUDGET_MB = int(os.environ.get("RAM_BUDGET_MB", "1200"))
LOW_RAM_BUDGET_CAP_MB = 500


@dataclass(frozen=True, slots=True)
class ResourceProfile:
    """Immutable runtime limits for sync/import and AI batch jobs."""

    low_ram: bool
    effective_ram_budget_mb: int
    max_sync_workers: int
    max_enrich_workers: int
    background_tests: bool
    ollama_gpu_fraction: float
    ollama_num_gpu: int


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "")
    if not raw:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def resolve_profile(*, low_ram: bool | None = None) -> ResourceProfile:
    """Map env vars into concrete worker and budget limits."""
    if low_ram is None:
        low_ram = _env_bool("LOW_RAM_MODE", False)

    if low_ram:
        budget = min(RAM_BUDGET_MB, LOW_RAM_BUDGET_CAP_MB)
        return ResourceProfile(
            low_ram=True,
            effective_ram_budget_mb=budget,
            max_sync_workers=1,
            max_enrich_workers=1,
            background_tests=False,
            ollama_gpu_fraction=0.0,
            ollama_num_gpu=0,
        )

    budget = int(RAM_BUDGET_MB * RESOURCE_RAM_FRACTION)
    workers = max(1, min(4, budget // 400))
    gpu_layers = max(0, int(100 * RESOURCE_GPU_FRACTION))
    return ResourceProfile(
        low_ram=False,
        effective_ram_budget_mb=budget,
        max_sync_workers=workers,
        max_enrich_workers=max(1, workers // 2),
        background_tests=_env_bool("TRINKER_BG_TESTS", True),
        ollama_gpu_fraction=RESOURCE_GPU_FRACTION,
        ollama_num_gpu=gpu_layers,
    )


def get_resource_profile() -> ResourceProfile:
    return resolve_profile()


def profile_snapshot() -> dict[str, Any]:
    """JSON-safe summary for logs and diagnostics."""
    prof = get_resource_profile()
    return {
        "low_ram_mode": prof.low_ram,
        "effective_ram_budget_mb": prof.effective_ram_budget_mb,
        "max_sync_workers": prof.max_sync_workers,
        "max_enrich_workers": prof.max_enrich_workers,
        "background_tests": prof.background_tests,
        "ollama_gpu_fraction": prof.ollama_gpu_fraction,
        "ollama_num_gpu": prof.ollama_num_gpu,
        "resource_ram_fraction": RESOURCE_RAM_FRACTION,
        "resource_gpu_fraction": RESOURCE_GPU_FRACTION,
        "ram_budget_mb": RAM_BUDGET_MB,
    }


def ollama_request_options() -> dict[str, Any]:
    """Extra Ollama options dict respecting GPU fraction policy."""
    prof = get_resource_profile()
    if prof.ollama_num_gpu <= 0:
        return {"num_gpu": 0}
    return {"num_gpu": prof.ollama_num_gpu}
