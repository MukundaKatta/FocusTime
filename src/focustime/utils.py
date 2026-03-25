"""Utility functions: time-block calculation, energy matching, scheduling."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any

from focustime.config import DayPlanConfig, PomodoroConfig


# ---------------------------------------------------------------------------
# Time-block helpers
# ---------------------------------------------------------------------------

def calculate_blocks(total_minutes: int, config: PomodoroConfig) -> list[dict[str, Any]]:
    """Break *total_minutes* of available work time into Pomodoro blocks.

    Returns a list of dicts, each with keys:
        block_number, type ("work" | "short_break" | "long_break"),
        duration_minutes, cumulative_minutes
    """
    blocks: list[dict[str, Any]] = []
    elapsed = 0
    work_count = 0

    while elapsed + config.work_duration <= total_minutes:
        work_count += 1
        elapsed += config.work_duration
        blocks.append({
            "block_number": len(blocks) + 1,
            "type": "work",
            "duration_minutes": config.work_duration,
            "cumulative_minutes": elapsed,
        })

        # Determine break type
        if work_count % config.long_break_interval == 0:
            break_dur = config.long_break
            break_type = "long_break"
        else:
            break_dur = config.short_break
            break_type = "short_break"

        # Only add break if there is room for another work block after it
        if elapsed + break_dur + config.work_duration <= total_minutes:
            elapsed += break_dur
            blocks.append({
                "block_number": len(blocks) + 1,
                "type": break_type,
                "duration_minutes": break_dur,
                "cumulative_minutes": elapsed,
            })

    return blocks


# ---------------------------------------------------------------------------
# Energy matching
# ---------------------------------------------------------------------------

def energy_match_score(task_energy: int, slot_energy: int) -> float:
    """Score how well a task's required energy matches the slot's energy.

    Returns a float in [0, 1] — 1.0 means perfect match.
    """
    diff = abs(task_energy - slot_energy)
    return max(0.0, 1.0 - diff * 0.25)


# ---------------------------------------------------------------------------
# Scheduling algorithm
# ---------------------------------------------------------------------------

def compute_task_score(
    task: dict[str, Any],
    slot_energy: int,
    elapsed_ratio: float = 0.0,
) -> float:
    """Compute a scheduling score for a task in a given time slot.

    Factors:
        - priority weight   (0-50)
        - energy match       (0-30)
        - urgency bonus for tasks that fit remaining time (0-20)

    Higher is better.
    """
    priority_score = (task["priority"] / 5.0) * 50.0
    energy_score = energy_match_score(task["energy_level"], slot_energy) * 30.0
    # Favour shorter tasks later in the day (clear the backlog)
    urgency_score = (1.0 - elapsed_ratio) * 20.0 * (1.0 - task["estimated_minutes"] / 240.0)
    return priority_score + energy_score + max(urgency_score, 0.0)


def schedule_tasks(
    tasks: list[dict[str, Any]],
    available_hours: float,
    day_config: DayPlanConfig,
    pomodoro_config: PomodoroConfig,
) -> list[dict[str, Any]]:
    """Assign tasks to Pomodoro blocks using a greedy best-fit algorithm.

    Returns a list of scheduled items, each containing:
        task, start_offset_minutes, block_count, score
    """
    total_minutes = int(available_hours * 60)
    blocks = calculate_blocks(total_minutes, pomodoro_config)
    work_blocks = [b for b in blocks if b["type"] == "work"]

    remaining_tasks = sorted(tasks, key=lambda t: t["priority"], reverse=True)
    schedule: list[dict[str, Any]] = []
    block_idx = 0

    while remaining_tasks and block_idx < len(work_blocks):
        current_block = work_blocks[block_idx]
        current_hour = day_config.start_hour + current_block["cumulative_minutes"] // 60
        slot_energy = day_config.get_energy_at_hour(current_hour % 24)
        elapsed_ratio = current_block["cumulative_minutes"] / max(total_minutes, 1)

        # Score each remaining task
        scored = [
            (t, compute_task_score(t, slot_energy, elapsed_ratio))
            for t in remaining_tasks
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        best_task, best_score = scored[0]
        blocks_needed = math.ceil(best_task["estimated_minutes"] / pomodoro_config.work_duration)
        blocks_available = len(work_blocks) - block_idx

        actual_blocks = min(blocks_needed, blocks_available)
        start_offset = current_block["cumulative_minutes"] - pomodoro_config.work_duration

        schedule.append({
            "task": best_task["name"],
            "priority": best_task["priority"],
            "energy_level": best_task["energy_level"],
            "estimated_minutes": best_task["estimated_minutes"],
            "start_offset_minutes": max(start_offset, 0),
            "block_count": actual_blocks,
            "score": round(best_score, 2),
        })

        block_idx += actual_blocks
        remaining_tasks.remove(best_task)

    return schedule


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_duration(minutes: int) -> str:
    """Human-readable duration string."""
    if minutes < 60:
        return f"{minutes}m"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m" if mins else f"{hours}h"


def timestamp_now() -> str:
    """ISO-8601 timestamp for the current moment."""
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"
