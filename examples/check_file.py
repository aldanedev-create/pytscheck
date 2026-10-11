#!/usr/bin/env python3
"""Check a single TypeScript file on disk.

Usage:

    python examples/check_file.py                    # uses a temp file
    python examples/check_file.py src/app.ts         # checks a real file
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from pytscheck import check_file


SAMPLE = """\
export interface User {
  name: string;
  age: number;
}

export const u: User = {
  name: "Alice",
  age: "thirty",   // <-- type error
};
"""


def _default_file() -> Path:
    """Write a sample file into a temp location and return its path."""
    tmp = Path(tempfile.mkdtemp(prefix="pytscheck-example-"))
    path = tmp / "sample.ts"
    path.write_text(SAMPLE, encoding="utf-8")
    return path


def main(argv: list[str]) -> int:
    if argv:
        target = Path(argv[0])
        if not target.exists():
            print(f"error: file does not exist: {target}", file=sys.stderr)
            return 2
    else:
        target = _default_file()
        print(f"(no file given; using {target})\n")

    print(f"Checking {target}")
    print()

    result = check_file(target)

    print(f"success: {result.success}")
    print(f"compiler: {result.compiler_version}")
    print(f"elapsed: {result.elapsed_seconds:.3f}s")
    print()

    if not result.diagnostics:
        print("No diagnostics.")
        return 0

    for d in result.diagnostics:
        location = f"{d.file}:{d.line}:{d.column}" if d.file else "<global>"
        print(f"  {d.category:<10} {location}  TS{d.code}")
        print(f"      {d.message}")

    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))