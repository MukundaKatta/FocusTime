# Architecture

## Overview

FocusTime is a Python library that merges the Pomodoro technique with an AI-driven task scheduler. The system assigns tasks to time blocks based on three signals: **priority**, **estimated duration**, and **energy level**.

## Module Map

```
src/focustime/
├── __init__.py      # Public API surface
├── config.py        # PomodoroConfig, DayPlanConfig, energy curves
├── core.py          # FocusTime class — session management, planning, export
└── utils.py         # Scheduling algorithm, block calculation, helpers
```

## Key Concepts

### Pomodoro Blocks

A session is divided into alternating work and break blocks:

| Block Type   | Default Duration | Frequency              |
|-------------|-----------------|------------------------|
| Work        | 25 min          | Every block            |
| Short Break | 5 min           | After each work block  |
| Long Break  | 15 min          | Every 4th work block   |

### Energy Curves

Energy curves map each hour of the day (0-23) to an energy level (1-5). Three built-in curves ship with the library:

- **morning_peak** — Energy peaks around 8-10 AM, fades in the afternoon.
- **afternoon_peak** — Energy builds after lunch, peaking around 1-3 PM.
- **steady** — Roughly constant energy during working hours.

Users can also supply a **custom** curve as a list of integers.

### Scheduling Algorithm

`schedule_tasks()` in `utils.py` implements a **greedy best-fit** algorithm:

1. Generate Pomodoro blocks from the available time budget.
2. For each work block, score every unscheduled task using:
   - **Priority weight** (0-50 points) — higher priority tasks score higher.
   - **Energy match** (0-30 points) — tasks whose energy requirement matches the slot's energy curve value score higher.
   - **Urgency bonus** (0-20 points) — shorter tasks get a bonus later in the day to encourage clearing the backlog.
3. Assign the highest-scored task to the current block(s).
4. Repeat until all blocks are filled or all tasks are assigned.

### Persistence

Session data and task logs are stored in a local SQLite database (`focustime.db` by default). This allows users to track historical productivity trends.

## Data Flow

```
User Input (tasks, config)
        │
        ▼
  ┌─────────────┐
  │  FocusTime   │  ← core.py
  │   (engine)   │
  └──────┬───────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
schedule   session
 tasks     blocks
    │         │
    ▼         ▼
  SQLite   Stats/Export
```

## Extensibility

- **Custom energy curves**: Pass `energy_curve="custom"` with a `custom_energy` list.
- **Config overrides**: All defaults can be changed via environment variables or constructor arguments.
- **Export formats**: JSON and CSV are built in; additional formats can be added by extending `export_schedule()`.
