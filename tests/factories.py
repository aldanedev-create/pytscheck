"""Factories for building test objects with sensible defaults.

Factories are *only* for pytscheck's own data types (Diagnostic, Result,
SourceFile, CompilerOptions). They are never used to fabricate compiler
output or fake subprocess results.
"""

from __future__ import annotations

from typing import Any

from pytscheck.config import CompilerOptions
from pytscheck.diagnostics import count_errors
from pytscheck.models import (
    Diagnostic,
    DiagnosticCategory,
    RelatedInformation,
    Result,
    SourceFile,
    SourceKind,
)


def make_diagnostic(
    *,
    file: str | None = "input.ts",
    line: int = 1,
    column: int = 1,
    code: int = 2322,
    category: DiagnosticCategory = "error",
    message: str = "Type 'string' is not assignable to type 'number'.",
    end_line: int | None = None,
    end_column: int | None = None,
    related: tuple[RelatedInformation, ...] = (),
    origin_file: str | None = None,
) -> Diagnostic:
    """Build a Diagnostic for tests that need one without running a compiler."""
    return Diagnostic(
        file=file,
        line=line,
        column=column,
        code=code,
        category=category,
        message=message,
        end_line=end_line,
        end_column=end_column,
        related=related,
        origin_file=origin_file,
    )


def make_result(
    *diagnostics: Diagnostic,
    compiler_version: str = "7.0.0-test",
    elapsed_seconds: float = 0.01,
    raw_output: str | None = None,
) -> Result:
    """Build a Result consistent with its diagnostics.

    ``success`` is derived, matching :func:`pytscheck.results.build_result`.
    """
    return Result(
        success=count_errors(diagnostics) == 0,
        diagnostics=tuple(diagnostics),
        compiler_version=compiler_version,
        elapsed_seconds=elapsed_seconds,
        raw_output=raw_output,
    )


def make_source_file(
    *,
    path: str = "App.ts",
    text: str = "export const x: number = 1;\n",
    origin_path: str | None = None,
    source_map: str | None = None,
    kind: SourceKind = "source",
    options: dict[str, Any] | None = None,
) -> SourceFile:
    return SourceFile(
        path=path,
        text=text,
        origin_path=origin_path,
        source_map=source_map,
        kind=kind,
        options=options if options is not None else {},
    )


def make_options(**overrides: Any) -> CompilerOptions:
    """Build a CompilerOptions with defaults, overriding specific fields."""
    defaults: dict[str, Any] = {
        "strict": True,
        "no_emit": True,
    }
    defaults.update(overrides)
    return CompilerOptions(**defaults)
