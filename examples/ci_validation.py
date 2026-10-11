#!/usr/bin/env python3
"""Fail a build on type errors.

Exit codes follow the pytscheck CLI convention:

    0  success -- no errors
    1  type errors reported
    2  usage error
    3  operational error (missing binary, crash, timeout, unparsable output)

This is the shape a CI script should take: distinguish "the code has
type errors" (1) from "the tool is broken" (3).

Usage:

    python examples/ci_validation.py src/          # check a directory
    python examples/ci_validation.py --strict src/ # fail if any errors
"""

from __future__ import annotations

import sys
from pathlib import Path

from pytscheck import check_project
from pytscheck.exceptions import (
    CompilerExecutionError,
    CompilerNotFoundError,
    CompilerTimeoutError,
    ConfigurationError,
    OutputParseError,
    PyTSCheckError,
    UnsupportedPlatformError,
)

EXIT_OK = 0
EXIT_TYPE_ERRORS = 1
EXIT_USAGE = 2
EXIT_OPERATIONAL = 3


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: ci_validation.py <project-directory>", file=sys.stderr)
        return EXIT_USAGE

    target = Path(argv[-1])
    if not target.is_dir():
        print(f"error: not a directory: {target}", file=sys.stderr)
        return EXIT_USAGE

    print(f"Type-checking {target}")

    try:
        result = check_project(target)
    except ConfigurationError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except (
        CompilerNotFoundError,
        CompilerTimeoutError,
        CompilerExecutionError,
        OutputParseError,
        UnsupportedPlatformError,
    ) as exc:
        print(f"operational error: {exc}", file=sys.stderr)
        return EXIT_OPERATIONAL
    except PyTSCheckError as exc:
        print(f"pytscheck error: {exc}", file=sys.stderr)
        return EXIT_OPERATIONAL

    print(f"compiler: {result.compiler_version}")
    print(f"elapsed:  {result.elapsed_seconds:.3f}s")
    print()

    if result.success:
        print("OK: no type errors")
        return EXIT_OK

    for d in result.errors:
        file = d.file or "<global>"
        print(f"{file}:{d.line}:{d.column}: {d.category} TS{d.code}: {d.message}")

    print()
    print(f"FAIL: {len(result.errors)} type error(s)")
    return EXIT_TYPE_ERRORS


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))