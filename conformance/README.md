# Compiler conformance

This suite compares actual PyTSCheck diagnostics with committed expectations for the pinned native compiler. It guards against unnoticed semantic/output drift; it does not implement TypeScript semantics independently.

## Run

```bash
python scripts/verify_conformance_cases.py
python conformance/run.py
python scripts/update_conformance.py --check
```

Install the package and bundled compiler before running. The current set has 63 cases covering assignability, inference, generics, functions, classes, unions, intersections, narrowing, nullability, modules, declarations, and compiler options.

## Files and ownership

| Path | Owner |
| --- | --- |
| `cases/` | `scripts/generate_conformance_cases.py` |
| `manifest.json` | Input generator's inventory/schema |
| `expected/` | `scripts/update_conformance.py --apply`, after review |
| `run.py` | Suite execution and comparison |

Expected JSON files are reviewable source baselines, not disposable build outputs. Changing compiler behavior requires reviewing the expected-output diff. The updater does not replace the generator-owned manifest.

## Update expectations

```bash
python scripts/update_conformance.py
# Inspect the staged differences, then only when intended:
python scripts/update_conformance.py --apply
python conformance/run.py
```

Default updater mode stages output instead of silently applying it. Use `--case` to select a case and `--help` for exact options. Update generators before modifying generated case inputs. Never approve a changed baseline solely because it makes CI green.

The CI workflow runs drift verification and conformance alongside integration, compatibility, security, fuzz, benchmarks, and packaging checks. See [testing](../docs/testing.md) and [compiler upgrades](../docs/compiler-upgrade.md).
