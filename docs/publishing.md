# Publishing PyTSCheck

The current version is `0.1.0.dev0`, a development release. Package versions in `pyproject.toml` and `src/pytscheck/version.py` must match; PyPI versions cannot be reused. The native compiler is pinned separately.

## Validate a checkout

```bash
python -m pip install -e ".[dev]" twine
python scripts/build_binaries.py linux-x64
python scripts/verify_binaries.py
python scripts/verify_fixtures.py --strict
python scripts/verify_benchmark_fixtures.py
python scripts/verify_conformance_cases.py
python -m ruff check src tests scripts conformance benchmarks
python -m ruff format --check src tests scripts conformance benchmarks
python -m mypy src/pytscheck
python -m pytest tests
python conformance/run.py
python scripts/release_check.py
```

Use `win32-x64` on Windows or `darwin-arm64` on Apple Silicon. Run the test suite serially: fault tests deliberately replace the bundled executable temporarily. Do not build packages or run another suite in the same checkout during those tests.

## Download distributions

The **Build PyPI distributions** Actions workflow produces one wheel and compiler bundle per platform, plus the source archive. Download the wheel artifacts from the successful run for the exact commit you intend to publish. The CI workflow separately runs native tests on Linux and install checks on Windows and macOS.

Each wheel includes exactly one native compiler, its TypeScript libraries, and upstream license and notices. Installing a wheel requires neither npm nor Node.js. Building from the source archive downloads the pinned compiler from npm during the build, so it requires network access unless the binary is already available in the checkout.

## Build locally

```bash
python -m build --sdist
python -m build --wheel
python -m twine check dist/*
```

For another target, set `PYTSCHECK_BUILD_PLATFORM` to an npm platform name from `supported-platforms.md` before `python -m build --wheel`. A cross-built wheel is not proof of native execution on that platform.

## Upload when ready

Extract the six wheel artifacts and source archive into one clean `dist/` directory. Verify that all artifacts have the intended package version and that their CI checks passed. Then:

```bash
python -m twine check dist/*
python -m twine upload --repository testpypi dist/*
# After verifying the TestPyPI installation:
python -m twine upload dist/*
```

Twine prompts for your PyPI token; use `__token__` as the username. Keep credentials out of the repository. This project does not publish automatically.
