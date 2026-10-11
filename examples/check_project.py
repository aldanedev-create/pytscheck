#!/usr/bin/env python3
"""Check a TypeScript project directory.

Usage:

    python examples/check_project.py                # uses a temp project
    python examples/check_project.py ./my-project   # checks a real project
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from pytscheck import check_project


TSCONFIG = """\
{
  "compilerOptions": {
    "strict": true,
    "noEmit": true,
    "target": "es2022",
    "module": "esnext"
  },
  "include": ["**/*.ts"]
}
"""

UTIL = """\
export function double(n: number): number {
  return n * 2;
}
"""

MAIN = """\
import { double } from "./util";

export const value: number = double(21);
export const broken: number = "not a number";   // <-- type error
"""


def _make_project() -> Path:
    root = Path(tempfile.mkdtemp(prefix="pytscheck-example-project-"))
    (root / "tsconfig.json").write_text(TSCONFIG, encoding="utf-8")
    (root / "util.ts").write_text(UTIL, encoding="utf-8")
    (root / "main.ts").write_text(MAIN, encoding="utf-8")
    return root


def main(argv: list[str]) -> int:
    if argv:
        root = Path(argv[0])
        if not root.is_dir():
            print(f"error: not a directory: {root}", file=sys.stderr)
            return 2
    else:
        root = _make_project()
        print(f"(no project given; using {root})")

    print(f"Checking project {root}")
    tsconfig = root / "tsconfig.json"
    print(f"  tsconfig: {'present' if tsconfig.exists() else 'absent'}")
    print()

    result = check_project(root)

    print(f"success: {result.success}")
    print(f"compiler: {result.compiler_version}")
    print(f"elapsed: {result.elapsed_seconds:.3f}s")
    print()

    if not result.diagnostics:
        print("No diagnostics.")
        return 0

    # Group by file for readability
    by_file: dict[str | None, list] = {}
    for d in result.diagnostics:
        by_file.setdefault(d.file, []).append(d)

    for file, diags in sorted(
        by_file.items(), key=lambda kv: kv[0] or ""
    ):
        print(f"{file or '<global>'}")
        for d in diags:
            print(f"  {d.line}:{d.column}  {d.category} TS{d.code}: {d.message}")
        print()

    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))