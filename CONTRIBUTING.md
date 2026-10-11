# Contributing to PyTSCheck

Thanks for your interest in contributing! This document explains how to set up a development environment, run checks, and submit changes.

## Development setup

Clone the repository and enter its directory. Replace `<repository-url>` with the actual GitHub clone URL:

```bash
git clone <repository-url> pytscheck
cd pytscheck
python -m venv .venv
```

Activate the virtual environment:

```bash
# Linux / macOS
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Install development dependencies and Git hooks:

```bash
python -m pip install -e ".[dev]"
pre-commit install
```

Fetch the bundled compiler for your platform:

```bash
# Replace linux-x64 with your platform, such as win32-x64 or darwin-arm64.
python scripts/build_binaries.py linux-x64
python scripts/verify_binaries.py
```

## Running checks

```bash
# Full test suite
pytest

# Fast subset
pytest -m "not slow"

# Lint
ruff check src tests scripts

# Check formatting without changing files
ruff format --check src tests scripts

# Apply formatting
ruff format src tests scripts

# Strict type checking
mypy --strict src/pytscheck

# Run all pre-commit hooks
pre-commit run --all-files
```

If configured, you can also use the task runners:

```bash
make test
task test
nox -s tests
```

## Project conventions

- **Minimum Python version:** 3.11. Modern syntax such as `X | Y`, `match`, and `slots=True` is welcome.
- **Typing:** `mypy --strict` must pass for `src/pytscheck`.
- **Formatting:** use `ruff format`, with a configured line length of 100.
- **Tests:** use one test file per module when practical. New behavior requires tests.
- **Public API:** anything exported from `pytscheck/__init__.py` is public and requires a docstring.
- **Adapters:** the core must not import consumer tools. Adapters live in the consuming package and register through the `pytscheck.adapters` entry-point group.

## Commit messages

Conventional Commits are preferred:

```text
feat(runner): add timeout handling
fix(protocol): correctly parse multi-line diagnostics
docs(adapters): document source-map contract
```

## Pull requests

- Keep each pull request focused on one logical change.
- Update `CHANGELOG.md` under `[Unreleased]`.
- Add or update tests. Test coverage must not decrease.
- Ensure CI passes on all supported Python versions and platforms.

## Reporting bugs

Use the issue templates under `.github/ISSUE_TEMPLATE/`.

For compiler incompatibilities, use the `compiler_compatibility.yml` template. Include reproduction steps, your platform, and relevant version information.

## Code of conduct

By participating, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).