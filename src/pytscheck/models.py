"""Core data models: diagnostics, results, and the adapter source model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

DiagnosticCategory = Literal["error", "warning", "suggestion", "message"]
SourceKind = Literal["source", "generated"]


@dataclass(frozen=True, slots=True)
class RelatedInformation:
    """Secondary location attached to a diagnostic."""

    file: str | None
    line: int
    column: int
    message: str


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A single compiler diagnostic, normalized to Python types.

    ``line`` and ``column`` are 1-based, matching tsgo's output.
    ``file`` is ``None`` for global/compiler-level diagnostics.
    ``origin_file`` is set after adapter remapping when applicable.
    """

    file: str | None
    line: int
    column: int
    code: int
    category: DiagnosticCategory
    message: str
    end_line: int | None = None
    end_column: int | None = None
    related: tuple[RelatedInformation, ...] = ()
    origin_file: str | None = None

    @property
    def is_error(self) -> bool:
        return self.category == "error"

    @property
    def is_warning(self) -> bool:
        return self.category == "warning"


@dataclass(frozen=True, slots=True)
class Result:
    """The outcome of a type check.

    ``success`` is True only when the compiler ran to completion *and*
    produced no errors. Operational failures raise instead of returning
    a Result with ``success=True``.
    """

    success: bool
    diagnostics: tuple[Diagnostic, ...]
    compiler_version: str
    elapsed_seconds: float
    raw_output: str | None = None

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        return tuple(d for d in self.diagnostics if d.category == "error")

    @property
    def warnings(self) -> tuple[Diagnostic, ...]:
        return tuple(d for d in self.diagnostics if d.category == "warning")


@dataclass(frozen=True, slots=True)
class SourceFile:
    """A TypeScript source handed to the checker, possibly virtual.

    Adapters produce these. ``path`` is the *virtual* path the checker
    sees (e.g. ``"App.vel.ts"``); ``origin_path`` is the real file the
    caller cares about (e.g. ``"static/js/App.vel"``). When ``source_map``
    is present, pytscheck remaps diagnostic positions back to
    ``origin_path``.
    """

    path: str
    text: str
    origin_path: str | None = None
    source_map: str | None = None
    kind: SourceKind = "source"
    options: dict[str, object] = field(default_factory=dict)


__all__ = [
    "Diagnostic",
    "DiagnosticCategory",
    "RelatedInformation",
    "Result",
    "SourceFile",
    "SourceKind",
]
