#!/usr/bin/env python3
"""Format diagnostics for humans and machines.

Usage:

    python examples/diagnostic_reporting.py           # human output
    python examples/diagnostic_reporting.py --json    # JSON output
"""

from __future__ import annotations

import json
import sys

from pytscheck import check
from pytscheck.diagnostics import count_by_category, summarize


SOURCE = """\
const a: number = "one";
const b: string = 2;
const c: boolean = "no";
"""


def _human_report(result) -> None:
    print(f"Checked: {result.compiler_version}")
    print(f"Elapsed: {result.elapsed_seconds * 1000:.1f} ms")
    print(f"Result:  {'PASS' if result.success else 'FAIL'}")
    print()

    if not result.diagnostics:
        print("No diagnostics.")
        return

    for d in result.diagnostics:
        file = d.file or "<global>"
        print(f"{file}:{d.line}:{d.column}")
        print(f"  {d.category} TS{d.code}: {d.message}")

    print()
    counts = count_by_category(result.diagnostics)
    print("Summary:")
    for category, n in sorted(counts.items()):
        print(f"  {category}: {n}")


def _json_report(result) -> None:
    payload = {
        "success": result.success,
        "compiler_version": result.compiler_version,
        "elapsed_seconds": result.elapsed_seconds,
        "diagnostics": [
            {
                "file": d.file,
                "line": d.line,
                "column": d.column,
                "code": d.code,
                "category": d.category,
                "message": d.message,
            }
            for d in result.diagnostics
        ],
        "summary": summarize(result.diagnostics),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    result = check(SOURCE)
    if as_json:
        _json_report(result)
    else:
        _human_report(result)
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))