"""
TRINKER - Per-step ideal timing calculator for overlay progress bars.
"""

from dataclasses import dataclass

from .models import BuildOrder, BuildStep


@dataclass
class StepTimingState:
    """Computed timing state for the current build step."""

    progress_pct: float  # 0–100 how far through this step window
    remaining_sec: int  # seconds until ideal step deadline
    status: str  # green | yellow | red | neutral
    target_time_str: str
    message: str


def _sec_to_mmss(sec: int) -> str:
    return f"{sec // 60}:{sec % 60:02d}"


def compute_step_timing(
    bo: BuildOrder,
    step_index: int,
    elapsed_sec: int,
) -> StepTimingState:
    """
    Calculate progress toward the ideal time for the current step.

    Each step's window runs from the previous step's time_sec to this step's time_sec.
    """
    if not bo.steps or step_index >= len(bo.steps):
        return StepTimingState(0, 0, "neutral", "", "No step")

    step: BuildStep = bo.steps[step_index]
    prev_time = bo.steps[step_index - 1].time_sec if step_index > 0 else 0
    target = step.time_sec

    if target <= 0:
        return StepTimingState(
            0,
            0,
            "neutral",
            step.time_str or "—",
            "No timing benchmark for this step",
        )

    window = max(target - prev_time, 1)
    elapsed_in_step = max(0, elapsed_sec - prev_time)
    progress = min(100.0, (elapsed_in_step / window) * 100.0)
    remaining = target - elapsed_sec

    if remaining > 15:
        status = "green"
        msg = f"{remaining}s to hit ideal ({step.time_str})"
    elif remaining >= 0:
        status = "yellow"
        msg = f"Hurry — {remaining}s left (target {step.time_str})"
    else:
        status = "red"
        msg = f"{abs(remaining)}s over ideal — move on!"

    return StepTimingState(
        progress_pct=progress,
        remaining_sec=remaining,
        status=status,
        target_time_str=step.time_str,
        message=msg,
    )
