"""Construction and invariants for :class:`Result`."""

from __future__ import annotations

from .diagnostics import count_errors, sort_diagnostics
from .models import Diagnostic, Result


def build_result(
    diagnostics: list[Diagnostic],
    *,
    compiler_version: str,
    elapsed_seconds: float,
    raw_output: str | None = None,
) -> Result:
    """Assemble a Result with diagnostics in deterministic order.

    ``success`` is True iff there are no error-category diagnostics.
    Callers that encounter operational failures must raise, not call this.
    """
    ordered = sort_diagnostics(diagnostics)
    return Result(
        success=count_errors(ordered) == 0,
        diagnostics=ordered,
        compiler_version=compiler_version,
        elapsed_seconds=elapsed_seconds,
        raw_output=raw_output,
    )


__all__ = ["build_result"]