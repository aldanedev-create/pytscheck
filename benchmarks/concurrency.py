"""Measure parallel check scaling.

Runs the same workload with N = 1, 2, 4, 8 threads and reports wall-clock
time, speedup, and efficiency for each.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"

WORKLOAD = ["tiny.ts"] * 8 + ["medium.ts"] * 4


def _run_sequential(paths: list[Path]) -> float:
    from pytscheck import check_file

    t0 = time.perf_counter()
    for p in paths:
        check_file(p)
    return time.perf_counter() - t0


def _run_parallel(paths: list[Path], workers: int) -> float:
    from pytscheck import check_file

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(check_file, paths))
    return time.perf_counter() - t0


def run() -> dict:
    paths = [FIXTURES / name for name in WORKLOAD]
    paths = [p for p in paths if p.exists()]
    if not paths:
        return {"error": "no fixtures found"}

    # Warm up once
    _run_sequential(paths[:1])

    sequential = _run_sequential(paths)
    data: dict = {
        "workload_size": len(paths),
        "sequential_seconds": sequential,
    }

    for workers in (2, 4, 8):
        elapsed = _run_parallel(paths, workers)
        speedup = sequential / elapsed if elapsed > 0 else 0.0
        data[f"workers_{workers}_seconds"] = elapsed
        data[f"workers_{workers}_speedup"] = speedup
        data[f"workers_{workers}_efficiency"] = speedup / workers

    return data