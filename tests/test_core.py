"""Tests for FocusTime core functionality."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from focustime import FocusTime
from focustime.config import PomodoroConfig
from focustime.utils import calculate_blocks, energy_match_score, compute_task_score


@pytest.fixture
def ft(tmp_path):
    """Provide a FocusTime instance with a temporary database."""
    db = str(tmp_path / "test.db")
    instance = FocusTime(db_path=db)
    yield instance
    instance.close()


class TestAddTask:
    def test_add_single_task(self, ft: FocusTime):
        task = ft.add_task("Write docs", priority=3, estimated_minutes=45, energy_level=2)
        assert task.name == "Write docs"
        assert task.priority == 3
        assert task.estimated_minutes == 45
        assert task.energy_level == 2
        assert task.completed is False

    def test_add_multiple_tasks(self, ft: FocusTime):
        ft.add_task("Task A", priority=5, estimated_minutes=30, energy_level=4)
        ft.add_task("Task B", priority=1, estimated_minutes=60, energy_level=1)
        ft.add_task("Task C", priority=3, estimated_minutes=25, energy_level=3)
        stats = ft.get_stats()
        assert stats["total_tasks"] == 3

    def test_invalid_priority_raises(self, ft: FocusTime):
        with pytest.raises(Exception):
            ft.add_task("Bad", priority=0, estimated_minutes=30, energy_level=3)
        with pytest.raises(Exception):
            ft.add_task("Bad", priority=6, estimated_minutes=30, energy_level=3)


class TestSession:
    def test_start_session_creates_blocks(self, ft: FocusTime):
        blocks = ft.start_session(duration_minutes=60)
        assert len(blocks) > 0
        work_blocks = [b for b in blocks if b["block_type"] == "work"]
        assert len(work_blocks) >= 1

    def test_complete_block_advances(self, ft: FocusTime):
        ft.start_session(duration_minutes=60)
        first = ft.get_current_block()
        assert first is not None
        completed = ft.complete_block()
        assert completed["completed"] is True
        second = ft.get_current_block()
        assert second is not None
        assert second["block_number"] != first["block_number"]

    def test_stats_after_work(self, ft: FocusTime):
        ft.start_session(duration_minutes=60)
        ft.complete_block()  # work block
        stats = ft.get_stats()
        assert stats["blocks_completed"] == 1
        assert stats["total_work_minutes"] == 25


class TestPlanning:
    def test_plan_day_returns_schedule(self, ft: FocusTime):
        ft.add_task("Code review", priority=5, estimated_minutes=50, energy_level=4)
        ft.add_task("Emails", priority=2, estimated_minutes=20, energy_level=1)
        schedule = ft.plan_day(available_hours=3, energy_curve="morning_peak")
        assert len(schedule) >= 1
        assert "task" in schedule[0]
        assert "score" in schedule[0]

    def test_suggest_next_task(self, ft: FocusTime):
        ft.add_task("Important", priority=5, estimated_minutes=30, energy_level=4)
        ft.add_task("Trivial", priority=1, estimated_minutes=10, energy_level=1)
        suggestion = ft.suggest_next_task()
        assert suggestion is not None
        assert suggestion["task"] == "Important"

    def test_export_json(self, ft: FocusTime):
        ft.add_task("Task X", priority=3, estimated_minutes=25, energy_level=3)
        ft.plan_day(available_hours=2)
        output = ft.export_schedule(format="json")
        data = json.loads(output)
        assert isinstance(data, list)

    def test_export_csv(self, ft: FocusTime):
        ft.add_task("Task Y", priority=4, estimated_minutes=50, energy_level=2)
        ft.plan_day(available_hours=4)
        output = ft.export_schedule(format="csv")
        assert "task" in output
        assert "Task Y" in output


class TestUtils:
    def test_calculate_blocks_count(self):
        config = PomodoroConfig()
        blocks = calculate_blocks(60, config)
        work = [b for b in blocks if b["type"] == "work"]
        assert len(work) == 2  # 25 + 5 + 25 = 55 <= 60

    def test_energy_match_perfect(self):
        assert energy_match_score(3, 3) == 1.0

    def test_energy_match_mismatch(self):
        score = energy_match_score(1, 5)
        assert score == 0.0

    def test_compute_task_score_high_priority(self):
        high = compute_task_score(
            {"priority": 5, "energy_level": 3, "estimated_minutes": 25}, 3
        )
        low = compute_task_score(
            {"priority": 1, "energy_level": 3, "estimated_minutes": 25}, 3
        )
        assert high > low
