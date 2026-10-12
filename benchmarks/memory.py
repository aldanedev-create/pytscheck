"""Measure peak memory per check.

Uses tracemalloc (portable) to measure the Python side. The compiler
subprocess has its own memory that this does not attribute, and the OS
accounts for it separately.
"""

from __future__ import annotations

import tracemalloc
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _measure_check(path: Path) -> dict:
    from pytscheck import check_file

    # Warm up so allocations from the first call are not counted.
    check_file(path)

    tracemalloc.start()
    try:
        check_file(path)
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    return {
        "source_bytes": path.stat().st_size,
        "current_bytes": current,
        "peak_bytes": peak,
        "ratio_peak_to_source": peak / path.stat().st_size if path.stat().st_size > 0 else 0.0,
    }


def run() -> dict:
    data: dict = {}

    for name in ("tiny.ts", "medium.ts", "large.ts", "errors-1000.ts"):
        p = FIXTURES / name
        if not p.exists():
            data[name] = {"error": "missing"}
            continue
        data[name] = _measure_check(p)

    # Project
    project = FIXTURES / "large-project"
    if project.is_dir() and (project / "tsconfig.json").exists():
        from pytscheck import check_project

        check_project(project)  # warmup

        tracemalloc.start()
        try:
            check_project(project)
            current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        total_bytes = sum(f.stat().st_size for f in project.rglob("*.ts"))
        data["large-project"] = {
            "source_bytes": total_bytes,
            "current_bytes": current,
            "peak_bytes": peak,
            "ratio_peak_to_source": peak / total_bytes if total_bytes > 0 else 0.0,
        }

    return data
