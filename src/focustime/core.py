"""Core FocusTime class — Pomodoro engine with AI-driven task scheduling."""

from __future__ import annotations

import json
import csv
import io
import sqlite3
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from focustime.config import DayPlanConfig, PomodoroConfig
from focustime.utils import (
    calculate_blocks,
    compute_task_score,
    format_duration,
    schedule_tasks,
    timestamp_now,
)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class Task(BaseModel):
    """A task to be scheduled."""

    name: str = Field(..., min_length=1, max_length=200)
    priority: int = Field(..., ge=1, le=5, description="1 (low) to 5 (critical)")
    estimated_minutes: int = Field(..., ge=1, le=480)
    energy_level: int = Field(..., ge=1, le=5, description="1 (low) to 5 (high)")
    completed: bool = False

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()


class Block(BaseModel):
    """A single Pomodoro work/break block."""

    block_number: int
    block_type: Literal["work", "short_break", "long_break"]
    duration_minutes: int
    task_name: str | None = None
    completed: bool = False


# ---------------------------------------------------------------------------
# FocusTime
# ---------------------------------------------------------------------------

class FocusTime:
    """Pomodoro + AI task scheduling engine.

    Usage:
        ft = FocusTime()
        ft.add_task("Write report", priority=4, estimated_minutes=60, energy_level=3)
        schedule = ft.plan_day(available_hours=6, energy_curve="morning_peak")
        ft.start_session(duration_minutes=25)
    """

    def __init__(self, config: PomodoroConfig | None = None, db_path: str | None = None):
        self.config = config or PomodoroConfig()
        if db_path is not None:
            self.config.db_path = db_path
        self._tasks: list[Task] = []
        self._blocks: list[Block] = []
        self._current_block_idx: int = -1
        self._blocks_completed: int = 0
        self._total_work_minutes: int = 0
        self._schedule: list[dict[str, Any]] = []
        self._init_db()

    # -- Database ------------------------------------------------------------

    def _init_db(self) -> None:
        """Initialise the SQLite database for persistence."""
        self._conn = sqlite3.connect(self.config.db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                blocks_completed INTEGER DEFAULT 0,
                total_work_minutes INTEGER DEFAULT 0
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                task_name TEXT NOT NULL,
                priority INTEGER,
                estimated_minutes INTEGER,
                energy_level INTEGER,
                completed INTEGER DEFAULT 0,
                logged_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    # -- Task management -----------------------------------------------------

    def add_task(
        self,
        name: str,
        priority: int,
        estimated_minutes: int,
        energy_level: int,
    ) -> Task:
        """Add a task to the backlog."""
        task = Task(
            name=name,
            priority=priority,
            estimated_minutes=estimated_minutes,
            energy_level=energy_level,
        )
        self._tasks.append(task)
        return task

    # -- Session / blocks ----------------------------------------------------

    def start_session(self, duration_minutes: int | None = None) -> list[dict[str, Any]]:
        """Start a Pomodoro session. Returns the list of generated blocks."""
        dur = duration_minutes or self.config.work_duration
        raw_blocks = calculate_blocks(dur, self.config)
        self._blocks = []
        for rb in raw_blocks:
            self._blocks.append(
                Block(
                    block_number=rb["block_number"],
                    block_type=rb["type"],
                    duration_minutes=rb["duration_minutes"],
                )
            )
        self._current_block_idx = 0 if self._blocks else -1
        # Persist session start
        cur = self._conn.execute(
            "INSERT INTO sessions (started_at) VALUES (?)",
            (timestamp_now(),),
        )
        self._session_id = cur.lastrowid
        self._conn.commit()
        return [b.model_dump() for b in self._blocks]

    def get_current_block(self) -> dict[str, Any] | None:
        """Return the current block or None."""
        if 0 <= self._current_block_idx < len(self._blocks):
            block = self._blocks[self._current_block_idx]
            remaining = block.duration_minutes  # simplified
            result = block.model_dump()
            result["remaining_minutes"] = remaining
            return result
        return None

    def complete_block(self) -> dict[str, Any] | None:
        """Mark the current block as complete and advance."""
        if self._current_block_idx < 0 or self._current_block_idx >= len(self._blocks):
            return None
        block = self._blocks[self._current_block_idx]
        block.completed = True
        if block.block_type == "work":
            self._blocks_completed += 1
            self._total_work_minutes += block.duration_minutes
        self._current_block_idx += 1
        return block.model_dump()

    def take_break(self, minutes: int | None = None) -> dict[str, Any]:
        """Record an explicit break."""
        dur = minutes or self.config.short_break
        is_long = (self._blocks_completed % self.config.long_break_interval == 0
                    and self._blocks_completed > 0)
        if minutes is None:
            dur = self.config.long_break if is_long else self.config.short_break
        return {
            "type": "long_break" if is_long else "short_break",
            "duration_minutes": dur,
            "blocks_completed_so_far": self._blocks_completed,
        }

    # -- Planning & scheduling -----------------------------------------------

    def plan_day(
        self,
        available_hours: float,
        energy_curve: str = "morning_peak",
        start_hour: int = 9,
    ) -> list[dict[str, Any]]:
        """Plan the day by scheduling tasks into Pomodoro blocks."""
        if not self._tasks:
            return []
        day_config = DayPlanConfig(
            start_hour=start_hour,
            energy_curve=energy_curve,
        )
        task_dicts = [t.model_dump() for t in self._tasks if not t.completed]
        self._schedule = schedule_tasks(task_dicts, available_hours, day_config, self.config)
        return self._schedule

    def suggest_next_task(self) -> dict[str, Any] | None:
        """Suggest the highest-scored uncompleted task for right now."""
        incomplete = [t for t in self._tasks if not t.completed]
        if not incomplete:
            return None
        from datetime import datetime

        current_hour = datetime.now().hour
        day_cfg = DayPlanConfig()
        slot_energy = day_cfg.get_energy_at_hour(current_hour)
        scored = [
            (t, compute_task_score(t.model_dump(), slot_energy))
            for t in incomplete
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        best_task, best_score = scored[0]
        return {
            "task": best_task.name,
            "priority": best_task.priority,
            "estimated_minutes": best_task.estimated_minutes,
            "energy_level": best_task.energy_level,
            "score": round(best_score, 2),
        }

    # -- Stats ---------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return session statistics."""
        total_tasks = len(self._tasks)
        completed_tasks = sum(1 for t in self._tasks if t.completed)
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "blocks_completed": self._blocks_completed,
            "total_work_minutes": self._total_work_minutes,
            "total_work_display": format_duration(self._total_work_minutes),
            "current_block": self._current_block_idx + 1 if self._current_block_idx >= 0 else 0,
            "total_blocks": len(self._blocks),
        }

    # -- Export --------------------------------------------------------------

    def export_schedule(self, format: str = "json") -> str:  # noqa: A002
        """Export the current schedule as JSON or CSV string."""
        data = self._schedule or []
        if format == "csv":
            buf = io.StringIO()
            if data:
                writer = csv.DictWriter(buf, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            return buf.getvalue()
        return json.dumps(data, indent=2)

    # -- Cleanup -------------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self, "_session_id"):
            self._conn.execute(
                "UPDATE sessions SET ended_at=?, blocks_completed=?, total_work_minutes=? WHERE id=?",
                (timestamp_now(), self._blocks_completed, self._total_work_minutes, self._session_id),
            )
            self._conn.commit()
        self._conn.close()

    def __enter__(self) -> "FocusTime":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
