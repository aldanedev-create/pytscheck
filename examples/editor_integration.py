#!/usr/bin/env python3
"""Minimal editor-style diagnostics pipeline.

An editor wants three things from a type checker:

    - diagnostics for a single file, fast
    - stable positions, so it can underline the right range
    - a clear distinction between "no errors" and "the checker failed"

This script shows the pattern: check one file, emit machine-readable
output on stdout, exit fast. It's the shape of an LSP-style backend.

Usage:

    python examples/editor_integration.py path/to/file.ts

Output on stdout is a JSON document with a fixed schema. Errors and
warnings are reported in the ``diagnostics`` array. Operational failures
are reported in the ``error`` field.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from pytscheck import check_file
from pytscheck.exceptions import PyTSCheckError


def main(argv: list[str]) -> int:
    if not argv:
        print(
            json.dumps({"error": "no file given"}),
        )
        return 2

    path = Path(argv[0])
    if not path.exists():
        print(json.dumps({"error": f"file not found: {path}"}))
        return 2

    start = time.perf_counter()
    try:
        result = check_file(path)
    except PyTSCheckError as exc:
        print(
            json.dumps(
                {
                    "file": str(path),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        )
        return 1
    elapsed_ms = (time.perf_counter() - start) * 1000

    diagnostics = [
        {
            "range": {
                "start": {"line": max(d.line - 1, 0), "character": max(d.column - 1, 0)},
                "end": {
                    "line": (d.end_line - 1) if d.end_line else max(d.line - 1, 0),
                    "character": (d.end_column - 1) if d.end_column else max(d.column - 1, 0),
                },
            },
            "severity": _severity(d.category),
            "code": f"TS{d.code}",
            "source": "pytscheck",
            "message": d.message,
        }
        for d in result.diagnostics
    ]

    print(
        json.dumps(
            {
                "file": str(path),
                "success": result.success,
                "compiler_version": result.compiler_version,
                "elapsed_ms": round(elapsed_ms, 3),
                "diagnostics": diagnostics,
            },
            indent=2,
        )
    )
    return 0


def _severity(category: str) -> int:
    """LSP severity: 1=Error, 2=Warning, 3=Information, 4=Hint."""
    return {
        "error": 1,
        "warning": 2,
        "suggestion": 3,
        "message": 4,
    }.get(category, 4)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))