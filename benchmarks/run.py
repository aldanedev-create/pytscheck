#!/usr/bin/env python3
"""Run the benchmark suite and report results.

Each benchmark is a module exposing `run() -> dict`. This script imports
every registered benchmark, runs it, and prints a report. With
`--save-baseline` or `--baseline`, it also writes or compares against a
recorded JSON snapshot.

Exit codes:
    0  ran successfully (or compared within tolerance)
    1  a benchmark failed to run, or exceeded the baseline tolerance
    2  usage error
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from collections.abc import Callable
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS = REPO_ROOT / "benchmarks"
FIXTURES = BENCHMARKS / "fixtures"

sys.path.insert(0, str(REPO_ROOT / "src"))


# ---------------------------------------------------------------------------
# Benchmark registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BenchmarkSpec:
    name: str
    module_filename: str
    description: str


BENCHMARK_SPECS: list[BenchmarkSpec] = [
    BenchmarkSpec("startup", "startup.py", "time-to-first-diagnostic"),
    BenchmarkSpec("throughput", "throughput.py", "diagnostics per second"),
    BenchmarkSpec("memory", "memory.py", "peak memory per check"),
    BenchmarkSpec("concurrency", "concurrency.py", "parallel check scaling"),
]


def _load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"_benchmark_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load benchmark module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkResult:
    name: str
    ok: bool
    elapsed: float
    data: dict = field(default_factory=dict)
    error: str = ""


# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------


def _binary_present() -> bool:
    try:
        from pytscheck.runner import binary_path

        binary_path()
        return True
    except Exception:
        return False


def _fixtures_present() -> bool:
    return FIXTURES.exists() and any(FIXTURES.glob("*.ts"))


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_one(spec: BenchmarkSpec) -> BenchmarkResult:
    start = time.monotonic()
    path = BENCHMARKS / spec.module_filename
    if not path.exists():
        return BenchmarkResult(
            name=spec.name,
            ok=False,
            elapsed=0.0,
            error=f"module missing: {path.relative_to(REPO_ROOT)}",
        )
    try:
        module = _load_module(path)
    except Exception as exc:
        return BenchmarkResult(
            name=spec.name,
            ok=False,
            elapsed=0.0,
            error=f"import failed: {type(exc).__name__}: {exc}",
        )

    run_fn: Callable[[], dict] | None = getattr(module, "run", None)
    if run_fn is None or not callable(run_fn):
        return BenchmarkResult(
            name=spec.name,
            ok=False,
            elapsed=0.0,
            error="module has no callable run()",
        )

    try:
        data = run_fn()
        if not isinstance(data, dict):
            raise TypeError("benchmark run() must return a dictionary")
        pending = [data]
        while pending:
            value = pending.pop()
            if value.get("error"):
                raise RuntimeError(str(value["error"]))
            pending.extend(item for item in value.values() if isinstance(item, dict))
    except Exception as exc:
        return BenchmarkResult(
            name=spec.name,
            ok=False,
            elapsed=time.monotonic() - start,
            error=f"run failed: {type(exc).__name__}: {exc}",
        )

    return BenchmarkResult(
        name=spec.name,
        ok=True,
        elapsed=time.monotonic() - start,
        data=data,
    )


# ---------------------------------------------------------------------------
# Baseline comparison
# ---------------------------------------------------------------------------


def _flatten(prefix: str, value: object) -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(value, dict):
        for k, v in value.items():
            out.update(_flatten(f"{prefix}.{k}" if prefix else k, v))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        out[prefix] = float(value)
    return out


def compare_baseline(
    current: list[BenchmarkResult],
    baseline_path: Path,
    tolerance: float,
) -> tuple[bool, list[str]]:
    if not baseline_path.exists():
        return False, [f"baseline not found: {baseline_path}"]
    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, [f"baseline is not valid JSON: {exc}"]

    baseline_flat: dict[str, float] = {}
    for bench in baseline.get("benchmarks", []):
        name = bench.get("name", "?")
        baseline_flat.update(_flatten(name, bench.get("data", {})))

    current_flat: dict[str, float] = {}
    for r in current:
        current_flat.update(_flatten(r.name, r.data))

    regressions: list[str] = []
    for key, base_value in baseline_flat.items():
        if base_value <= 0:
            continue
        cur_value = current_flat.get(key)
        if cur_value is None:
            continue
        higher_is_better = key.endswith(("_per_second", "_speedup", "_efficiency"))
        delta = (
            base_value - cur_value if higher_is_better else cur_value - base_value
        ) / base_value
        if delta > tolerance:
            regressions.append(
                f"{key}: {base_value:.3f} -> {cur_value:.3f} "
                f"({delta * 100:.1f}% regression, tolerance {tolerance * 100:.1f}%)"
            )

    return not regressions, regressions


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _print_results(results: list[BenchmarkResult]) -> None:
    for r in results:
        status = "OK  " if r.ok else "FAIL"
        print(f"{status} {r.name}  ({r.elapsed:.2f}s)")
        if not r.ok:
            print(f"      {r.error}")
            continue
        for key, value in _flatten("", r.data).items():
            print(f"      {key}: {value:.4f}")


def _to_json(results: list[BenchmarkResult]) -> dict:
    return {
        "benchmarks": [
            {
                "name": r.name,
                "ok": r.ok,
                "elapsed": r.elapsed,
                "error": r.error,
                "data": r.data,
            }
            for r in results
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="benchmarks",
        description="Run PyTSCheck's benchmark suite.",
    )
    parser.add_argument(
        "--only",
        action="append",
        metavar="NAME",
        help="run only the named benchmark(s)",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--save-baseline",
        type=Path,
        metavar="PATH",
        help="write results to PATH as a baseline",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        metavar="PATH",
        help="compare against a recorded baseline",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.10,
        help="fractional slowdown tolerance (default: 0.10)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list available benchmarks and exit",
    )
    args = parser.parse_args(argv)
    report_stream = sys.stderr if args.json else sys.stdout
    report = partial(print, file=report_stream)

    if args.list:
        for spec in BENCHMARK_SPECS:
            report(f"{spec.name:12s} {spec.description}")
        return 0

    if not _binary_present():
        report(
            "error: bundled tsgo not present; run scripts/build_binaries.py <platform> first",
            file=sys.stderr,
        )
        return 1
    if not _fixtures_present():
        report(
            "error: benchmark fixtures missing; "
            "run scripts/generate_benchmark_fixtures.py --manifest",
            file=sys.stderr,
        )
        return 1

    specs = BENCHMARK_SPECS
    if args.only:
        wanted = set(args.only)
        specs = [s for s in specs if s.name in wanted]
        if not specs:
            report(f"no benchmarks matched: {sorted(wanted)}", file=sys.stderr)
            return 2

    results: list[BenchmarkResult] = []
    for spec in specs:
        report(f"==> {spec.name}")
        result = run_one(spec)
        results.append(result)
        status = "OK  " if result.ok else "FAIL"
        report(f"    {status} ({result.elapsed:.2f}s)")
        if not result.ok:
            report(f"    {result.error}")

    report()
    with redirect_stdout(report_stream):
        _print_results(results)

    if args.save_baseline:
        args.save_baseline.parent.mkdir(parents=True, exist_ok=True)
        args.save_baseline.write_text(
            json.dumps(_to_json(results), indent=2) + "\n",
            encoding="utf-8",
        )
        report(f"\nbaseline written: {args.save_baseline}")

    if args.baseline:
        ok, regressions = compare_baseline(results, args.baseline, args.tolerance)
        if ok:
            report(f"\nbaseline comparison OK (tolerance {args.tolerance:.0%})")
        else:
            report("\nbaseline comparison FAILED:")
            for r in regressions:
                report(f"  {r}")
            return 1

    if args.json:
        print(json.dumps(_to_json(results), indent=2))

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
