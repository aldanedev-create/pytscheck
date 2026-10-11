"""Measure time-to-first-diagnostic.

Breaks a single check into phases so we can see where time is spent:

    import      Python import cost
    locate      platform detection + binary path resolution
    spawn+run   the compiler subprocess
    parse       the parser
    total       end-to-end

Also runs a warmup loop to distinguish first-call cost from steady state.
"""

from __future__ import annotations

import time
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"
TINY = FIXTURES / "tiny.ts"


def _time_import() -> float:
    # The import already happened by the time this function runs; instead,
    # measure a cold import in a subprocess.
    import subprocess
    import sys

    code = "import time; t0=time.perf_counter(); import pytscheck; print(time.perf_counter()-t0)"
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        shell=False,
    )
    if result.returncode != 0:
        return -1.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return -1.0


def _time_locate() -> float:
    from pytscheck.runner import binary_path

    t0 = time.perf_counter()
    binary_path()
    return time.perf_counter() - t0


def _time_single_check() -> tuple[float, float]:
    """Return (spawn+run time, parse time) for a single tiny check."""
    from pytscheck import check_file

    # The check_file call includes spawn+run+parse+result construction.
    # We measure the whole thing; the "parse" component is not separately
    # observable from outside pytscheck, so we report the total per check.
    t0 = time.perf_counter()
    check_file(TINY)
    return time.perf_counter() - t0, 0.0


def _warmup(n: int = 5) -> list[float]:
    from pytscheck import check_file

    times: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        check_file(TINY)
        times.append(time.perf_counter() - t0)
    return times


def run() -> dict:
    if not TINY.exists():
        return {"error": "tiny.ts not found"}

    data: dict = {}

    data["import_seconds"] = _time_import()
    data["locate_binary_seconds"] = _time_locate()

    spawn_and_parse, _ = _time_single_check()
    data["single_check_seconds"] = spawn_and_parse

    warm = _warmup(5)
    data["warmup_mean_seconds"] = sum(warm) / len(warm)
    data["warmup_min_seconds"] = min(warm)
    data["warmup_max_seconds"] = max(warm)

    data["tiny_file_bytes"] = TINY.stat().st_size

    return data