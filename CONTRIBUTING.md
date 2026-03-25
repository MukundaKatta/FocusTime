# Contributing to FocusTime

Thank you for considering a contribution to FocusTime! We welcome bug reports, feature requests, and pull requests.

## Getting Started

1. **Fork & clone** the repository.
2. Create a virtual environment and install dev dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   make install
   ```
3. Create a feature branch:
   ```bash
   git checkout -b feat/my-feature
   ```

## Development Workflow

```bash
make test       # Run the test suite
make lint       # Lint with ruff
make format     # Auto-format with ruff
make typecheck  # Type-check with mypy
```

## Pull Request Guidelines

- Keep PRs focused on a single change.
- Include tests for new functionality.
- Ensure all checks pass (`make all`).
- Write clear commit messages following [Conventional Commits](https://www.conventionalcommits.org/).

## Code Style

- We use **ruff** for linting and formatting.
- Type hints are required for all public functions.
- Target Python 3.10+.

## Reporting Issues

Open an issue on GitHub with:
- A clear description of the bug or feature request.
- Steps to reproduce (for bugs).
- Expected vs. actual behaviour.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
