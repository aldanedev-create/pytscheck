
"""Check an in-memory TypeScript source string.

Usage:

    python examples/check_string.py
    python examples/check_string.py 'const x: number = "wrong";'
"""

from __future__ import annotations

import sys

from pytscheck import check


DEFAULT_SOURCE = """\
const greeting: string = "hello";
const age: number = "twenty";        // <-- type error
export { greeting, age };
"""


def main(argv: list[str]) -> int:
    source = argv[0] if argv else DEFAULT_SOURCE

    print("Source:")
    for i, line in enumerate(source.splitlines(), start=1):
        print(f"  {i:>3} | {line}")
    print()

    result = check(source)

    print(f"success: {result.success}")
    print(f"compiler: {result.compiler_version}")
    print(f"elapsed: {result.elapsed_seconds:.3f}s")
    print()

    if result.success:
        print("No diagnostics.")
        return 0

    print(f"{len(result.errors)} error(s):")
    for d in result.errors:
        location = f"{d.file}:{d.line}:{d.column}" if d.file else "<global>"
        print(f"  {location}  TS{d.code}  {d.message}")

    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))