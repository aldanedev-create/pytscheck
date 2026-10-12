"""Diagnostic construction, normalization, ordering, and filtering.

This module is deliberately dependency-light: it operates on
:class:`~pytscheck.models.Diagnostic` objects only and knows nothing about
the compiler, the runner, or adapters.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from .models import Diagnostic, DiagnosticCategory, RelatedInformation

__all__ = [
    "count_by_category",
    "count_errors",
    "count_warnings",
    "deduplicate",
    "filter_by_category",
    "filter_by_code",
    "filter_by_file",
    "group_by_file",
    "has_errors",
    "make_related",
    "sort_diagnostics",
    "summarize",
    "worst_category",
]


_CATEGORY_SEVERITY: dict[DiagnosticCategory, int] = {
    "error": 3,
    "warning": 2,
    "suggestion": 1,
    "message": 0,
}


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def sort_diagnostics(diags: Iterable[Diagnostic]) -> tuple[Diagnostic, ...]:
    """Return diagnostics in a deterministic order.

    Sort key, in order:

    1. ``file is None`` last (global diagnostics after file diagnostics)
    2. file path (empty string for globals)
    3. line
    4. column
    5. code
    6. message (final tiebreaker for stability across platforms)

    The result is a tuple so it's hashable and safe to store in
    :class:`~pytscheck.models.Result`.
    """
    return tuple(
        sorted(
            diags,
            key=lambda d: (
                d.file is None,
                d.file or "",
                d.line,
                d.column,
                d.code,
                d.message,
            ),
        )
    )


def deduplicate(diags: Iterable[Diagnostic]) -> tuple[Diagnostic, ...]:
    """Remove exact duplicates while preserving order.

    Two diagnostics are equal if every field matches. This is used after
    adapter remapping, where several virtual positions can collapse onto
    the same original position.
    """
    seen: set[Diagnostic] = set()
    out: list[Diagnostic] = []
    for d in diags:
        if d in seen:
            continue
        seen.add(d)
        out.append(d)
    return tuple(out)


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def filter_by_category(
    diags: Iterable[Diagnostic], category: DiagnosticCategory
) -> tuple[Diagnostic, ...]:
    return tuple(d for d in diags if d.category == category)


def filter_by_file(diags: Iterable[Diagnostic], file: str) -> tuple[Diagnostic, ...]:
    """Return diagnostics whose ``file`` matches exactly."""
    return tuple(d for d in diags if d.file == file)


def filter_by_code(diags: Iterable[Diagnostic], code: int) -> tuple[Diagnostic, ...]:
    """Return diagnostics with the given TS error code."""
    return tuple(d for d in diags if d.code == code)


# ---------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------


def count_errors(diags: Iterable[Diagnostic]) -> int:
    """Number of error-category diagnostics."""
    return sum(1 for d in diags if d.category == "error")


def count_warnings(diags: Iterable[Diagnostic]) -> int:
    """Number of warning-category diagnostics."""
    return sum(1 for d in diags if d.category == "warning")


def count_by_category(diags: Iterable[Diagnostic]) -> dict[DiagnosticCategory, int]:
    """Counts per category. Missing categories are absent from the dict."""
    counts: dict[DiagnosticCategory, int] = {}
    for d in diags:
        counts[d.category] = counts.get(d.category, 0) + 1
    return counts


def has_errors(diags: Iterable[Diagnostic]) -> bool:
    """True iff any error-category diagnostic is present."""
    return any(d.category == "error" for d in diags)


def worst_category(diags: Iterable[Diagnostic]) -> DiagnosticCategory | None:
    """Return the most severe category present, or None if empty.

    Severity: error > warning > suggestion > message.
    """
    best: DiagnosticCategory | None = None
    best_rank = -1
    for d in diags:
        rank = _CATEGORY_SEVERITY[d.category]
        if rank > best_rank:
            best_rank = rank
            best = d.category
    return best


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------


def group_by_file(
    diags: Iterable[Diagnostic],
) -> dict[str | None, tuple[Diagnostic, ...]]:
    """Group diagnostics by their ``file`` field.

    ``None`` key holds global/compiler diagnostics. Values are tuples in
    the order encountered.
    """
    groups: dict[str | None, list[Diagnostic]] = {}
    for d in diags:
        groups.setdefault(d.file, []).append(d)
    return {k: tuple(v) for k, v in groups.items()}


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def summarize(diags: Iterable[Diagnostic]) -> dict[str, object]:
    """Return a small JSON-serializable summary.

    Intended for CI output, logs, and editor integrations.
    """
    diags_t = tuple(diags)
    return {
        "total": len(diags_t),
        "errors": count_errors(diags_t),
        "warnings": count_warnings(diags_t),
        "by_category": {k: v for k, v in count_by_category(diags_t).items()},
        "files": sorted({d.file for d in diags_t if d.file is not None}),
        "has_global": any(d.file is None for d in diags_t),
    }


# ---------------------------------------------------------------------------
# Construction helpers
# ---------------------------------------------------------------------------


def make_related(
    file: str | None,
    line: int,
    column: int,
    message: str,
) -> RelatedInformation:
    """Construct a :class:`RelatedInformation` with positional args."""
    return RelatedInformation(file=file, line=line, column=column, message=message)


# ---------------------------------------------------------------------------
# Iteration convenience
# ---------------------------------------------------------------------------


def iter_errors(diags: Iterable[Diagnostic]) -> Iterator[Diagnostic]:
    """Yield only error-category diagnostics."""
    for d in diags:
        if d.category == "error":
            yield d


def iter_warnings(diags: Iterable[Diagnostic]) -> Iterator[Diagnostic]:
    """Yield only warning-category diagnostics."""
    for d in diags:
        if d.category == "warning":
            yield d
