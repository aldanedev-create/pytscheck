"""Reusable assertion helpers for pytscheck tests."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from pytscheck.models import Diagnostic, Result


def assert_valid_result(result: Result) -> None:
    """Invariants every Result must satisfy."""
    assert isinstance(result, Result)
    assert isinstance(result.success, bool)
    assert isinstance(result.diagnostics, tuple)
    assert all(isinstance(d, Diagnostic) for d in result.diagnostics)
    assert isinstance(result.compiler_version, str) and result.compiler_version
    assert isinstance(result.elapsed_seconds, float)
    assert result.elapsed_seconds >= 0.0
    assert result.raw_output is None or isinstance(result.raw_output, str)

    assert isinstance(result.errors, tuple)
    assert isinstance(result.warnings, tuple)
    assert all(d.category == "error" for d in result.errors)
    assert all(d.category == "warning" for d in result.warnings)

    expected = not any(d.category == "error" for d in result.diagnostics)
    assert result.success is expected, (
        f"success={result.success} but errors present={[d.message for d in result.errors]}"
    )


def assert_diagnostics_equal(actual: Sequence[Diagnostic], expected: Sequence[Diagnostic]) -> None:
    assert len(actual) == len(expected), (
        f"count mismatch: {len(actual)} != {len(expected)}\n"
        f"actual  : {[(d.file, d.line, d.column, d.code) for d in actual]}\n"
        f"expected: {[(d.file, d.line, d.column, d.code) for d in expected]}"
    )
    for a, e in zip(actual, expected, strict=True):
        assert a == e, f"\nactual  : {a}\nexpected: {e}"


def assert_diagnostic_ordering(diags: Sequence[Diagnostic]) -> None:
    """Diagnostics must be ordered by (has_file, file, line, column, code, message)."""
    keys = [(d.file is None, d.file or "", d.line, d.column, d.code, d.message) for d in diags]
    assert keys == sorted(keys), f"diagnostics are not deterministically ordered: {keys}"


def assert_no_diagnostics(result: Result) -> None:
    assert result.success, f"expected success, got diagnostics: {result.diagnostics}"
    assert result.diagnostics == ()


def assert_has_error_code(result: Result, code: int) -> None:
    codes = {d.code for d in result.errors}
    assert code in codes, f"expected error TS{code}, got codes: {sorted(codes)}"


def assert_has_diagnostic_matching(result: Result, pattern: str) -> None:
    rx = re.compile(pattern)
    for d in result.diagnostics:
        if rx.search(d.message):
            return
    messages = [d.message for d in result.diagnostics]
    raise AssertionError(f"no diagnostic matches {pattern!r}; got: {messages}")


def assert_all_in(names: Iterable[str], container: Iterable[str]) -> None:
    missing = set(names) - set(container)
    assert not missing, f"missing: {sorted(missing)}"
