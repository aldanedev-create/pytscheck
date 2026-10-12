# Testing and validation

Install development dependencies and download your platform compiler first. See [development](development.md).

## Main suite

```bash
python -m pytest tests
python -m pytest tests/test_protocol.py -q
python -m pytest tests/integration -q
python -m pytest tests/compatibility -q
python -m pytest tests/security -q
python -m pytest tests/fuzz -q
```

Tests deliberately remove/replace the bundled compiler to exercise failures. Run the suite serially and do not build or run another suite concurrently in the same checkout. Expected platform skips do not establish execution coverage for that other platform. A missing binary can skip real compiler tests, so always verify it exists before interpreting a green result.

## Fixture drift

```bash
python scripts/verify_fixtures.py --strict
python scripts/verify_benchmark_fixtures.py
python scripts/verify_conformance_cases.py
```

Generated inputs and their manifests must match the generators. Update the appropriate generator, regenerate deliberately, review the diff, and commit; do not change fixtures merely to suppress a failure.

## Conformance

```bash
python conformance/run.py
python scripts/update_conformance.py --check
```

The 63 pinned cases cover assignability, inference, generics, functions, classes, unions, intersections, narrowing, nullability, modules, declarations, and compiler options. The runner compares actual compiler diagnostics with committed expectations. See [compiler upgrades](compiler-upgrade.md) for changing those expectations.

## Run staged checks

```bash
python scripts/run_all_tests.py
python scripts/run_all_tests.py --only integration --only conformance
```

Stages are `unit`, `integration`, `compatibility`, `security`, `fuzz`, `conformance`, `benchmarks`, and `wheel-install`. This runs actual checks; it does not regenerate expected outputs.

## Release gate

```bash
python scripts/release_check.py
python scripts/release_check.py --wheel-only
```

The gate validates version/license/platform consistency, fixture and compiler integrity, tests, conformance, builds, wheel contents, and clean offline installation. Compatibility and broader lint/type checks also run separately in CI.

## CI

`ci.yml` tests Python 3.11–3.13, integration/compatibility/security/fuzz/conformance, benchmarks, the release gate, and native macOS/Windows compatibility and built-wheel installation. `distributions.yml` builds all six wheels and the source archive. Both must pass for the exact commit being released.

CI sets `FORCE_COLOR=1`; to reproduce locally on POSIX, also use `TERM=xterm-256color`. The runner requests plain diagnostics independently of those settings.
