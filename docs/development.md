# Development

## Set up a checkout

```bash
git clone https://github.com/aldanedev-create/pytscheck.git
cd pytscheck
python -m venv .venv
```

Activate `.venv` using `source .venv/bin/activate` on Linux/macOS or `.\.venv\Scripts\Activate.ps1` in PowerShell. If PowerShell activation is unavailable, use `.\.venv\Scripts\python.exe` directly in place of `python`.

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]" twine
python scripts/build_binaries.py linux-x64
python scripts/verify_binaries.py
```

Choose your [platform identifier](supported-platforms.md). Development dependencies include pytest, Ruff, mypy, build tooling, and fixture/testing tools. They are not installed for normal users.

## Repository layout

| Directory | Purpose |
| --- | --- |
| `src/pytscheck/` | Python API, subprocess runner, diagnostics, adapter protocol |
| `src/pytscheck/bin/` | Downloaded native compilers and manifests |
| `tests/` | Unit, integration, compatibility, security, fuzz, adapter tests |
| `scripts/` | Fixture generation/verification, binary builds, release gate |
| `conformance/` | Pinned TypeScript cases and expected outputs |
| `benchmarks/` | Real compiler performance measurements |
| `examples/` | Standalone usage scripts |
| `docs/` | User and maintainer guides |
| `.github/workflows/` | CI and distribution builds |

## Run checks

```bash
python -m ruff check src tests scripts conformance benchmarks
python -m ruff format --check src tests scripts conformance benchmarks
python -m mypy src/pytscheck
python -m pytest tests
python conformance/run.py
```

Run compiler-mutating tests serially, with no other test suite or build using that checkout. See [testing](testing.md) for fixture checks and targeted commands.

## Build

```bash
python -m build --sdist
python -m build --wheel
python -m twine check dist/*
```

A normal wheel build targets the current host and fetches the compiler if needed. Development editable installs skip that fetch. See [binary distribution](binary-distribution.md) for cross-building and [publishing](publishing.md) for an all-platform release.

## Contribute

Keep public API/exception behavior compatible, document observable changes, and use real compiler executions for integration behavior. Update the changelog and relevant guides. Follow [CONTRIBUTING.md](../CONTRIBUTING.md).
