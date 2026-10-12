"""Parser for tsgo's diagnostic output.

This module is the single place that knows tsgo's textual format. If tsgo
gains a machine-readable mode, only this file changes.

Phase-0 note: the exact format is not yet verified. The parser below
handles the classic tsc shape:

    path/to/file.ts(12,34): error TS2322: Type 'string' is not assignable
    to type 'number'.

    path/to/file.ts(12,5): error TS1005: ';' expected.

Multi-line messages continue with indented lines. A robust fallback
(``parse_unstructured``) captures unknown lines so nothing is silently
dropped; callers surface them as operational errors.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .exceptions import OutputParseError
from .models import Diagnostic, DiagnosticCategory

# path(line,col): category TS code: message
_HEADER = re.compile(
    r"^(?P<file>.+?)\((?P<line>\d+),(?P<col>\d+)\):\s+"
    r"(?P<category>error|warning|suggestion|message)\s+"
    r"(?P<code>TS\d+):\s+(?P<message>.*)$"
)

# path(line,col): category TS code: message  — end position variant
_HEADER_RANGE = re.compile(
    r"^(?P<file>.+?)\((?P<line>\d+),(?P<col>\d+)-(?P<endline>\d+),(?P<endcol>\d+)\):\s+"
    r"(?P<category>error|warning|suggestion|message)\s+"
    r"(?P<code>TS\d+):\s+(?P<message>.*)$"
)

# Bare file with no position (global diagnostics)
_HEADER_GLOBAL = re.compile(
    r"^(?P<category>error|warning|suggestion|message)\s+"
    r"(?P<code>TS\d+):\s+(?P<message>.*)$"
)

_CATEGORY_MAP: dict[str, DiagnosticCategory] = {
    "error": "error",
    "warning": "warning",
    "suggestion": "suggestion",
    "message": "message",
}


@dataclass(frozen=True, slots=True)
class ParseReport:
    """Result of parsing: diagnostics plus any lines we could not classify."""

    diagnostics: tuple[Diagnostic, ...]
    unparsed_lines: tuple[str, ...]


def _strip_ts(code: str) -> int:
    return int(code[2:])  # strip leading "TS"


def parse(output: str) -> ParseReport:
    """Parse tsgo textual output into diagnostics."""
    diagnostics: list[Diagnostic] = []
    unparsed: list[str] = []

    pending: Diagnostic | None = None
    pending_message_lines: list[str] = []

    def flush() -> None:
        nonlocal pending, pending_message_lines
        if pending is None:
            return
        if pending_message_lines:
            joined = pending.message + "\n" + "\n".join(pending_message_lines)
            pending = Diagnostic(
                file=pending.file,
                line=pending.line,
                column=pending.column,
                end_line=pending.end_line,
                end_column=pending.end_column,
                code=pending.code,
                category=pending.category,
                message=joined,
                related=pending.related,
                origin_file=pending.origin_file,
            )
        diagnostics.append(pending)
        pending = None
        pending_message_lines = []

    for raw_line in output.splitlines():
        line = raw_line.rstrip()

        if not line:
            flush()
            continue

        # Continuation line: leading whitespace and we have a pending diagnostic
        if pending is not None and raw_line[:1].isspace():
            pending_message_lines.append(line.strip())
            continue

        m = _HEADER_RANGE.match(line) or _HEADER.match(line)
        if m:
            flush()
            gd = m.groupdict()
            end_line = int(gd["endline"]) if gd.get("endline") else None
            end_col = int(gd["endcol"]) if gd.get("endcol") else None
            pending = Diagnostic(
                file=gd["file"],
                line=int(gd["line"]),
                column=int(gd["col"]),
                end_line=end_line,
                end_column=end_col,
                code=_strip_ts(gd["code"]),
                category=_CATEGORY_MAP[gd["category"]],
                message=gd["message"],
            )
            continue

        mg = _HEADER_GLOBAL.match(line)
        if mg:
            flush()
            gd = mg.groupdict()
            pending = Diagnostic(
                file=None,
                line=0,
                column=0,
                code=_strip_ts(gd["code"]),
                category=_CATEGORY_MAP[gd["category"]],
                message=gd["message"],
            )
            continue

        unparsed.append(line)

    flush()
    return ParseReport(diagnostics=tuple(diagnostics), unparsed_lines=tuple(unparsed))


def parse_or_raise(output: str, *, allow_unparsed: bool = False) -> tuple[Diagnostic, ...]:
    """Parse, raising :class:`OutputParseError` on unclassifiable content."""
    report = parse(output)
    if report.unparsed_lines and not allow_unparsed:
        preview = "\n".join(report.unparsed_lines[:10])
        raise OutputParseError(
            f"could not parse {len(report.unparsed_lines)} line(s) of tsgo output:\n{preview}",
            raw_output=output,
        )
    return report.diagnostics


__all__ = ["ParseReport", "parse", "parse_or_raise"]
