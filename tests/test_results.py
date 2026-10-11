"""Tests for pytscheck.results."""

from __future__ import annotations

import pytest

from pytscheck.diagnostics import sort_diagnostics
from pytscheck.models import Diagnostic, Result
from pytscheck.results import build_result


def _d(
    file: str | None = "a.ts",
    line: int = 1,
    code: int = 2322,
    category: str = "error",
) -> Diagnostic:
    return Diagnostic(
        file=file,
        line=line,
        column=1,
        code=code,
        category=category,  # type: ignore[arg-type]
        message="m",
    )


def test_build_result_empty_is_success() -> None:
    r = build_result([], compiler_version="7.0.0", elapsed_seconds=0.01)
    assert isinstance(r, Result)
    assert r.success is True
    assert r.diagnostics == ()


def test_build_result_with_errors_fails() -> None:
    r = build_result([_d()], compiler_version="7.0.0", elapsed_seconds=0.01)
    assert r.success is False
    assert len(r.errors) == 1


def test_build_result_with_only_warnings_succeeds() -> None:
    r = build_result(
        [_d(category="warning")],
        compiler_version="7.0.0",
        elapsed_seconds=0.01,
    )
    assert r.success is True
    assert len(r.warnings) == 1


def test_build_result_orders_diagnostics() -> None:
    items = [_d(file="b.ts", line=3), _d(file="a.ts", line=1), _d(file=None, line=0)]
    r = build_result(items, compiler_version="7.0.0", elapsed_seconds=0.01)
    assert r.diagnostics == sort_diagnostics(items)


def test_build_result_is_deterministic() -> None:
    items = [_d(file="b.ts"), _d(file="a.ts"), _d(file="a.ts", line=2)]
    a = build_result(items, compiler_version="7.0.0", elapsed_seconds=0.0)
    b = build_result(items, compiler_version="7.0.0", elapsed_seconds=0.0)
    assert a.diagnostics == b.diagnostics


def test_build_result_attaches_metadata() -> None:
    r = build_result(
        [],
        compiler_version="7.1.0-dev",
        elapsed_seconds=1.25,
        raw_output="raw",
    )
    assert r.compiler_version == "7.1.0-dev"
    assert r.elapsed_seconds == 1.25
    assert r.raw_output == "raw"


def test_build_result_raw_output_defaults_to_none() -> None:
    r = build_result([], compiler_version="7.0.0", elapsed_seconds=0.0)
    assert r.raw_output is None


def test_build_result_returns_tuple_diagnostics() -> None:
    r = build_result([_d()], compiler_version="7.0.0", elapsed_seconds=0.0)
    assert isinstance(r.diagnostics, tuple)


def test_build_result_errors_and_warnings_are_consistent() -> None:
    items = [
        _d(category="error"),
        _d(category="warning"),
        _d(category="suggestion"),
        _d(category="message"),
    ]
    r = build_result(items, compiler_version="7.0.0", elapsed_seconds=0.0)
    assert len(r.errors) == 1
    assert len(r.warnings) == 1
    # success iff no errors
    assert r.success is False


def test_build_result_success_iff_no_errors() -> None:
    for items in ([], [_d(category="warning")], [_d(category="error")]):
        r = build_result(items, compiler_version="7.0.0", elapsed_seconds=0.0)
        expected = not any(d.category == "error" for d in items)
        assert r.success is expected


def test_build_result_duplicate_diagnostics_are_kept() -> None:
    """build_result does not deduplicate; that is a caller concern."""
    items = [_d(), _d()]
    r = build_result(items, compiler_version="7.0.0", elapsed_seconds=0.0)
    assert len(r.diagnostics) == 2


def test_results_all_names_exist() -> None:
    from pytscheck import results

    for name in results.__all__:
        assert hasattr(results, name), f"missing: {name}"