"""Unit tests for Result invariants.

The invariants are documented in the Result docstring and enforced by
build_result(). They must hold under every code path that produces a
Result.
"""

from __future__ import annotations

import dataclasses

import pytest

from pytscheck.diagnostics import count_errors, sort_diagnostics
from pytscheck.models import Diagnostic, Result
from pytscheck.results import build_result
from tests.factories import make_diagnostic


def _d(**kw) -> Diagnostic:
    return make_diagnostic(**kw)


# --- construction ----------------------------------------------------------


def test_build_result_returns_result_instance() -> None:
    r = build_result([], compiler_version="x", elapsed_seconds=0.0)
    assert isinstance(r, Result)


def test_build_result_empty_is_success() -> None:
    r = build_result([], compiler_version="x", elapsed_seconds=0.0)
    assert r.success is True
    assert r.diagnostics == ()


def test_build_result_with_error_is_failure() -> None:
    r = build_result([_d(category="error")], compiler_version="x", elapsed_seconds=0.0)
    assert r.success is False


def test_build_result_with_warning_is_success() -> None:
    r = build_result(
        [_d(category="warning")], compiler_version="x", elapsed_seconds=0.0
    )
    assert r.success is True


# --- invariants ------------------------------------------------------------


def test_invariant_diagnostics_is_tuple() -> None:
    r = build_result([_d()], compiler_version="x", elapsed_seconds=0.0)
    assert isinstance(r.diagnostics, tuple)


def test_invariant_errors_is_tuple() -> None:
    r = build_result([_d()], compiler_version="x", elapsed_seconds=0.0)
    assert isinstance(r.errors, tuple)


def test_invariant_warnings_is_tuple() -> None:
    r = build_result([_d(category="warning")], compiler_version="x", elapsed_seconds=0.0)
    assert isinstance(r.warnings, tuple)


def test_invariant_errors_are_errors() -> None:
    r = build_result([_d(category="error")], compiler_version="x", elapsed_seconds=0.0)
    for d in r.errors:
        assert d.category == "error"


def test_invariant_warnings_are_warnings() -> None:
    r = build_result([_d(category="warning")], compiler_version="x", elapsed_seconds=0.0)
    for d in r.warnings:
        assert d.category == "warning"


def test_invariant_success_iff_no_errors() -> None:
    for diags in ([], [_d(category="warning")], [_d(category="error")]):
        r = build_result(diags, compiler_version="x", elapsed_seconds=0.0)
        expected = not any(d.category == "error" for d in diags)
        assert r.success is expected


def test_invariant_diagnostics_ordered() -> None:
    diags = [_d(file="b.ts"), _d(file="a.ts"), _d(file=None)]
    r = build_result(diags, compiler_version="x", elapsed_seconds=0.0)
    assert r.diagnostics == sort_diagnostics(diags)


def test_invariant_compiler_version_nonempty() -> None:
    r = build_result([], compiler_version="7.0.0", elapsed_seconds=0.0)
    assert r.compiler_version
    assert isinstance(r.compiler_version, str)


def test_invariant_elapsed_seconds_nonnegative() -> None:
    r = build_result([], compiler_version="x", elapsed_seconds=1.5)
    assert r.elapsed_seconds >= 0.0


def test_invariant_raw_output_default_none() -> None:
    r = build_result([], compiler_version="x", elapsed_seconds=0.0)
    assert r.raw_output is None


def test_invariant_raw_output_can_be_set() -> None:
    r = build_result(
        [], compiler_version="x", elapsed_seconds=0.0, raw_output="some output"
    )
    assert r.raw_output == "some output"


# --- frozen / hashable ------------------------------------------------------


def test_result_is_frozen() -> None:
    r = build_result([], compiler_version="x", elapsed_seconds=0.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.success = False  # type: ignore[misc]


def test_result_is_hashable() -> None:
    r = build_result([], compiler_version="x", elapsed_seconds=0.0)
    assert hash(r) == hash(r)


# --- counts match -----------------------------------------------------------


def test_errors_count_matches_count_errors() -> None:
    diags = [_d(category="error"), _d(category="warning"), _d(category="error")]
    r = build_result(diags, compiler_version="x", elapsed_seconds=0.0)
    assert len(r.errors) == count_errors(r.diagnostics)


def test_warnings_count_matches() -> None:
    diags = [_d(category="warning"), _d(category="warning"), _d(category="error")]
    r = build_result(diags, compiler_version="x", elapsed_seconds=0.0)
    assert len(r.warnings) == sum(1 for d in diags if d.category == "warning")


# --- edge cases -------------------------------------------------------------


def test_many_diagnostics() -> None:
    diags = [_d(file=f"f{i}.ts", line=i) for i in range(1000)]
    r = build_result(diags, compiler_version="x", elapsed_seconds=0.0)
    assert len(r.diagnostics) == 1000
    assert r.success is False


def test_global_only_diagnostics() -> None:
    diags = [_d(file=None)]
    r = build_result(diags, compiler_version="x", elapsed_seconds=0.0)
    assert r.success is False
    assert r.diagnostics[0].file is None


def test_mixed_global_and_file_diagnostics_ordering() -> None:
    diags = [_d(file="a.ts"), _d(file=None), _d(file="b.ts")]
    r = build_result(diags, compiler_version="x", elapsed_seconds=0.0)
    files = [d.file for d in r.diagnostics]
    # Global (None) must come last
    assert files == ["a.ts", "b.ts", None]