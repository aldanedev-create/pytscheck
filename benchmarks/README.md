# Benchmarks

The benchmark runner measures real bundled compiler invocations. Correctness lives in `tests/` and `conformance/`; timing measurements do not replace them.

## Run

```bash
python benchmarks/run.py --list
python benchmarks/run.py --json > benchmarks.json
python benchmarks/run.py --json --save-baseline baseline.json
python benchmarks/run.py --baseline baseline.json --tolerance 0.10
```

Install the package and compiler first. `--json` keeps stdout machine-readable and sends progress to stderr. Use the runner's `--help` for selecting benchmark families.

## Families

| Family | Measures |
| --- | --- |
| `startup` | Time to first diagnostic |
| `throughput` | Diagnostic production/processing throughput |
| `memory` | Python-side peak memory per check |
| `concurrency` | Scaling with parallel checks |

Memory observations do not represent all native compiler child-process memory. Concurrent checks launch separate compiler processes. Compare baselines on the same machine with comparable Python/compiler versions and environment; absolute ranges or promised speedups are not inferred from CI.

Generated benchmark fixtures and their manifest must pass `python scripts/verify_benchmark_fixtures.py`. To modify inputs, change `scripts/generate_benchmark_fixtures.py`, regenerate, and review the diff. The runner's registered benchmark specification owns the family list.

See [performance](../docs/performance.md), [testing](../docs/testing.md), and the dated [benchmark audit](audit-2026-10-12.md). Historical audit observations describe their recorded checkout and do not replace current runs.
