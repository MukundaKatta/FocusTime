# FocusTime — Pomodoro + AI task scheduling — energy-aware planning, smart task suggestion, productivity stats

Pomodoro + AI task scheduling — energy-aware planning, smart task suggestion, productivity stats.

## Why FocusTime

FocusTime exists to make this workflow practical. Pomodoro + ai task scheduling — energy-aware planning, smart task suggestion, productivity stats. It favours a small, inspectable surface over sprawling configuration.

## Features

- `Task` — exported from `src/focustime/core.py`
- `Block` — exported from `src/focustime/core.py`
- `FocusTime` — exported from `src/focustime/core.py`
- Included test suite
- Dedicated documentation folder

## Tech Stack

- **Runtime:** Python
- **Tooling:** Pydantic

## How It Works

The codebase is organised into `docs/`, `src/`, `tests/`. The primary entry points are `src/focustime/core.py`, `src/focustime/__init__.py`. `src/focustime/core.py` exposes `Task`, `Block`, `FocusTime` — the core types that drive the behaviour.

## Getting Started

```bash
pip install -e .
```

## Usage

```python
from focustime.core import Task

instance = Task()
# See the source for the full API
```

## Project Structure

```
FocusTime/
├── .env.example
├── CONTRIBUTING.md
├── Makefile
├── README.md
├── docs/
├── pyproject.toml
├── src/
├── tests/
```