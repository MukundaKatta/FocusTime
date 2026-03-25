"""Configuration defaults and energy curve definitions for FocusTime."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class PomodoroConfig:
    """Pomodoro timer configuration."""

    work_duration: int = int(os.getenv("FOCUSTIME_WORK_DURATION", "25"))
    short_break: int = int(os.getenv("FOCUSTIME_SHORT_BREAK", "5"))
    long_break: int = int(os.getenv("FOCUSTIME_LONG_BREAK", "15"))
    long_break_interval: int = int(os.getenv("FOCUSTIME_LONG_BREAK_INTERVAL", "4"))
    db_path: str = os.getenv("FOCUSTIME_DB_PATH", "focustime.db")


# Pre-defined energy curves.
# Each maps an hour-of-day (0-23) to a relative energy level (1-5).
ENERGY_CURVES: dict[str, list[int]] = {
    "morning_peak": [
        1, 1, 1, 1, 1, 2,   # 00-05
        3, 4, 5, 5, 4, 4,   # 06-11
        3, 3, 2, 2, 2, 3,   # 12-17
        2, 2, 1, 1, 1, 1,   # 18-23
    ],
    "afternoon_peak": [
        1, 1, 1, 1, 1, 1,   # 00-05
        2, 2, 3, 3, 3, 3,   # 06-11
        4, 5, 5, 5, 4, 3,   # 12-17
        3, 2, 2, 1, 1, 1,   # 18-23
    ],
    "steady": [
        1, 1, 1, 1, 1, 2,   # 00-05
        3, 3, 3, 3, 3, 3,   # 06-11
        3, 3, 3, 3, 3, 3,   # 12-17
        2, 2, 1, 1, 1, 1,   # 18-23
    ],
}


@dataclass
class DayPlanConfig:
    """Configuration for daily planning."""

    start_hour: int = 9
    energy_curve: str = os.getenv("FOCUSTIME_DEFAULT_ENERGY_CURVE", "morning_peak")
    custom_energy: list[int] = field(default_factory=list)

    def get_energy_at_hour(self, hour: int) -> int:
        """Return energy level (1-5) for a given hour."""
        if self.energy_curve == "custom" and self.custom_energy:
            idx = hour % len(self.custom_energy)
            return self.custom_energy[idx]
        curve = ENERGY_CURVES.get(self.energy_curve, ENERGY_CURVES["morning_peak"])
        return curve[hour % 24]
