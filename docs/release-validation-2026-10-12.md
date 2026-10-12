# Release validation — 2026-10-12

Package: `0.1.0.dev0` (development release). Compiler: `7.0.0-dev.20260707.2`.

## Verification

- Linux x64, Python 3.12: all 1,407 cases exercised; 1,372 passed and 35 platform/environment skips after fixes. Compiler-mutating tests run serially; other tests run with four workers. The final isolated temporary-directory regression was rerun successfully.
- Full release gate passes: version, licenses, platforms, fixture drift, manifest, bundled compiler, pytest (compatibility tested separately), 63 conformance cases, source/wheel build, wheel contents and clean installation.
- Final bounded-read improvement: 48 focused runner/security tests pass; one expected stderr-output skip. Six benchmark regression tests pass.
- Ruff check and formatting pass for 197 files; strict mypy passes for 26 source files.
- All four benchmarks run successfully with real compiler output. JSON output is machine readable. Measurements are informational, from this hosted Linux environment with `GOMAXPROCS=2`.
- All six npm archives pass upstream SHA-512 verification. On-disk binaries pass checksum/size verification. All wheels carry a platform tag, one compiler, TypeScript libraries, and upstream notices. Binary architecture headers verified.
- Rebuilt source archive and six wheels pass `twine check`. Rebuilt Linux wheel passes clean offline installation and valid/error checks with an empty PATH.

## Changes

Repair adapter source arguments, source validation, option-list serialization, bounded output capture and timeout process cleanup. Repair stale compiler expectations, multiprocessing pickling, temporary-directory isolation and failure-test file restoration. Generate fixture manifests and pinned conformance expectations without disabling gates. Build self-contained platform wheels, with macOS 12 minimum verified from the binaries. Make the all-tests script run tests rather than regenerate conformance expectations.

## Publication

See [publishing.md](publishing.md). Upload the intended version only after reviewing GitHub CI. Windows/macOS native compatibility and wheel-install checks are in CI; cross-built artifacts are not a claim of native execution for all six targets. PyPI publication is a separate user action.

## Final CI follow-up

Commit `dbfd46459fe69fecf3d1f137d70309db0999a611` fixes color-capable terminal diagnostics, direct compiler comparisons, and Python 3.11 protocol assertions. The full local suite with `FORCE_COLOR=1` and `TERM=xterm-256color` passes: **1,373 passed, 35 expected skips**. Ruff checks/formatting pass for 197 files; strict mypy passes for 26 source files.

[CI run 38209232090](https://github.com/aldanedev-create/pytscheck/actions/runs/38209232090) succeeds across Python 3.11–3.13, integration, compatibility, security, fuzz, conformance, benchmarks, release gate, and native Windows/macOS wheel builds/installations. [Distribution run 38209232079](https://github.com/aldanedev-create/pytscheck/actions/runs/38209232079) builds all six wheels and the source archive successfully. These runs validate that commit; later documentation artifacts must be built from their own intended release commit.
