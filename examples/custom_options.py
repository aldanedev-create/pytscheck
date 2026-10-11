#!/usr/bin/env python3
"""Control the compiler with CompilerOptions.

Usage:

    python examples/custom_options.py
"""

from __future__ import annotations

from pytscheck import CompilerOptions, check


SOURCE = """\
// Under strict mode, this is an error:
export function len(s: string | null): number {
  return s.length;
}
"""


def _run(label: str, options: CompilerOptions) -> None:
    print(f"--- {label} ---")
    print(f"options: strict={options.strict} "
          f"no_emit={options.no_emit} "
          f"target={options.target!r}")
    print()

    result = check(SOURCE, options=options)

    print(f"success: {result.success}")
    if result.errors:
        for d in result.errors:
            print(f"  {d.line}:{d.column}  TS{d.code}: {d.message}")
    print()


def main() -> int:
    # 1. Default: strict=True, no_emit=True
    _run("default options", CompilerOptions())

    # 2. Strict off: the null check disappears
    _run(
        "strict off",
        CompilerOptions(strict=False),
    )

    # 3. Explicit target/module
    _run(
        "es2022 / esnext",
        CompilerOptions(
            target="es2022",
            module="esnext",
            module_resolution="bundler",
        ),
    )

    # 4. Extra options passed through
    _run(
        "with skipLibCheck",
        CompilerOptions(skip_lib_check=True),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())