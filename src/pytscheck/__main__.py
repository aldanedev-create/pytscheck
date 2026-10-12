"""``python -m pytscheck`` and the ``pytscheck`` console script.

This module is intentionally small. It exposes three things:

- ``--version``  : print pytscheck / compiler / protocol versions
- ``--where``    : print the path to the bundled tsgo binary
- ``check``      : a minimal CLI over the public API (Phase 2+)

Every subcommand maps to a public function in :mod:`pytscheck.api`. The
CLI never reimplements logic: it parses arguments, calls the API, and
formats the result.

Exit codes
----------

  0  success (no errors)
  1  type errors were reported
  2  usage / configuration error
  3  operational failure (missing binary, crash, timeout, unparsable output)

The distinction between 1 and 3 matters for CI: a tool that wants to fail
the build on type errors should treat 1 as a normal failure and 3 as an
infrastructure problem.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .exceptions import (
    CompilerExecutionError,
    CompilerNotFoundError,
    CompilerTimeoutError,
    ConfigurationError,
    OutputParseError,
    PyTSCheckError,
    UnsupportedPlatformError,
)
from .models import Diagnostic, Result
from .version import ADAPTER_PROTOCOL_VERSION, COMPILER_VERSION, __version__

EXIT_OK = 0
EXIT_TYPE_ERRORS = 1
EXIT_USAGE = 2
EXIT_OPERATIONAL = 3


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pytscheck",
        description="Type-check TypeScript from Python.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print versions and exit",
    )
    parser.add_argument(
        "--where",
        action="store_true",
        help="print the path to the bundled tsgo binary and exit",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # --- check string -----------------------------------------------------
    p_str = sub.add_parser("string", help="check an in-memory source string")
    p_str.add_argument("source", help="TypeScript source text")
    p_str.add_argument("--filename", default="input.ts", help="virtual filename")
    p_str.add_argument("--json", action="store_true", help="emit JSON diagnostics")
    p_str.add_argument("--keep-raw", action="store_true", help="include raw compiler output")

    # --- check file -------------------------------------------------------
    p_file = sub.add_parser("file", help="check a single file")
    p_file.add_argument("path", type=Path, help="path to a .ts / .tsx / .mts / .cts file")
    p_file.add_argument("--json", action="store_true", help="emit JSON diagnostics")
    p_file.add_argument("--keep-raw", action="store_true", help="include raw compiler output")

    # --- check project ----------------------------------------------------
    p_proj = sub.add_parser("project", help="check a project directory")
    p_proj.add_argument("root", type=Path, help="project root directory")
    p_proj.add_argument("--json", action="store_true", help="emit JSON diagnostics")
    p_proj.add_argument("--keep-raw", action="store_true", help="include raw compiler output")

    return parser


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def _format_diagnostic(d: Diagnostic) -> str:
    """One-line, grep-friendly rendering of a diagnostic."""
    loc = f"{d.file or '<global>'}({d.line},{d.column})"
    return f"{loc}: {d.category} TS{d.code}: {d.message}"


def _print_result(result: Result, *, as_json: bool) -> None:
    if as_json:
        import json

        payload = {
            "success": result.success,
            "compiler_version": result.compiler_version,
            "elapsed_seconds": result.elapsed_seconds,
            "diagnostics": [
                {
                    "file": d.file,
                    "origin_file": d.origin_file,
                    "line": d.line,
                    "column": d.column,
                    "end_line": d.end_line,
                    "end_column": d.end_column,
                    "code": d.code,
                    "category": d.category,
                    "message": d.message,
                }
                for d in result.diagnostics
            ],
        }
        print(json.dumps(payload, indent=2))
        return

    for d in result.diagnostics:
        print(_format_diagnostic(d))
    if result.success:
        print(f"ok ({result.elapsed_seconds:.2f}s)")
    else:
        n = len(result.errors)
        print(f"{n} error{'s' if n != 1 else ''} ({result.elapsed_seconds:.2f}s)")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _cmd_version() -> int:
    print(f"pytscheck {__version__}")
    print(f"bundled compiler {COMPILER_VERSION}")
    print(f"adapter protocol {ADAPTER_PROTOCOL_VERSION}")
    return EXIT_OK


def _cmd_where() -> int:
    from .runner import binary_path

    try:
        print(binary_path())
    except PyTSCheckError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_OPERATIONAL
    return EXIT_OK


def _cmd_check(args: argparse.Namespace) -> int:
    # Import lazily so --version / --where never pull in the runner.
    from .api import check, check_file, check_project

    try:
        if args.command == "string":
            result = check(
                args.source,
                filename=args.filename,
                keep_raw=args.keep_raw,
            )
        elif args.command == "file":
            result = check_file(args.path, keep_raw=args.keep_raw)
        elif args.command == "project":
            result = check_project(args.root, keep_raw=args.keep_raw)
        else:  # pragma: no cover - argparse enforces this
            print(f"unknown command: {args.command}", file=sys.stderr)
            return EXIT_USAGE
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

    _print_result(result, as_json=args.json)
    return EXIT_OK if result.success else EXIT_TYPE_ERRORS


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        return _cmd_version()
    if args.where:
        return _cmd_where()

    if args.command in {"string", "file", "project"}:
        return _cmd_check(args)

    parser.print_help()
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
