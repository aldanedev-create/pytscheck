"""Tests for pytscheck.models."""

from __future__ import annotations

import dataclasses

import pytest

from pytscheck.models import (
    Diagnostic,
    DiagnosticCategory,
    RelatedInformation,
    Result,
    SourceFile,
    SourceKind,
)

# --- Diagnostic -------------------------------------------------------------


def _d(**overrides: object) -> Diagnostic:
    base: dict[str, object] = {
        "file": "a.ts",
        "line": 1,
        "column": 1,
        "code": 2322,
        "category": "error",
        "message": "m",
    }
    base.update(overrides)
    return Diagnostic(**base)  # type: ignore[arg-type]


def test_diagnostic_is_frozen() -> None:
    d = _d()
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.line = 2  # type: ignore[misc]


def test_diagnostic_is_hashable() -> None:
    d = _d()
    assert hash(d) == hash(d)
    assert {d} == {d}


def test_diagnostic_equality_and_inequality() -> None:
    a = _d()
    b = _d()
    c = _d(line=2)
    assert a == b
    assert a != c


def test_diagnostic_is_error_and_is_warning() -> None:
    assert _d(category="error").is_error
    assert not _d(category="error").is_warning
    assert _d(category="warning").is_warning
    assert not _d(category="warning").is_error
    assert not _d(category="suggestion").is_error
    assert not _d(category="suggestion").is_warning


def test_diagnostic_defaults() -> None:
    d = _d()
    assert d.end_line is None
    assert d.end_column is None
    assert d.related == ()
    assert d.origin_file is None


def test_diagnostic_accepts_none_file() -> None:
    d = _d(file=None)
    assert d.file is None


def test_diagnostic_accepts_related_information() -> None:
    r = RelatedInformation(file="b.ts", line=5, column=3, message="because")
    d = _d(related=(r,))
    assert d.related == (r,)


def test_diagnostic_origin_file_is_separate_from_file() -> None:
    d = _d(file="App.ts", origin_file="App.vel")
    assert d.file == "App.ts"
    assert d.origin_file == "App.vel"


@pytest.mark.parametrize("category", ["error", "warning", "suggestion", "message"])
def test_diagnostic_accepts_all_categories(category: DiagnosticCategory) -> None:
    d = _d(category=category)
    assert d.category == category


# --- RelatedInformation -----------------------------------------------------


def test_related_information_is_frozen() -> None:
    r = RelatedInformation(file="b.ts", line=5, column=3, message="because")
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.line = 1  # type: ignore[misc]


def test_related_information_is_hashable() -> None:
    r = RelatedInformation(file="b.ts", line=5, column=3, message="because")
    assert hash(r) == hash(r)


# --- Result -----------------------------------------------------------------


def test_result_errors_and_warnings_are_derived() -> None:
    e = _d(category="error")
    w = _d(category="warning")
    r = Result(
        success=False,
        diagnostics=(e, w),
        compiler_version="7.0.0",
        elapsed_seconds=0.1,
    )
    assert r.errors == (e,)
    assert r.warnings == (w,)


def test_result_errors_and_warnings_are_tuples() -> None:
    r = Result(
        success=True,
        diagnostics=(),
        compiler_version="7.0.0",
        elapsed_seconds=0.0,
    )
    assert isinstance(r.errors, tuple)
    assert isinstance(r.warnings, tuple)


def test_result_stores_success_explicitly_not_recomputed() -> None:
    """Result.success is stored, not derived. It is set by build_result()."""
    e = _d(category="error")
    r = Result(
        success=True,  # intentionally inconsistent
        diagnostics=(e,),
        compiler_version="7.0.0",
        elapsed_seconds=0.1,
    )
    assert r.success is True


def test_result_is_frozen() -> None:
    r = Result(
        success=True,
        diagnostics=(),
        compiler_version="7.0.0",
        elapsed_seconds=0.0,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.success = False  # type: ignore[misc]


def test_result_raw_output_default() -> None:
    r = Result(
        success=True,
        diagnostics=(),
        compiler_version="7.0.0",
        elapsed_seconds=0.0,
    )
    assert r.raw_output is None


def test_result_is_hashable_when_fields_are() -> None:
    r = Result(
        success=True,
        diagnostics=(),
        compiler_version="7.0.0",
        elapsed_seconds=0.0,
    )
    assert hash(r) == hash(r)


# --- SourceFile -------------------------------------------------------------


def test_source_file_defaults() -> None:
    s = SourceFile(path="App.ts", text="export const x = 1;\n")
    assert s.path == "App.ts"
    assert s.text == "export const x = 1;\n"
    assert s.origin_path is None
    assert s.source_map is None
    assert s.kind == "source"
    assert s.options == {}


def test_source_file_options_isolated_per_instance() -> None:
    a = SourceFile(path="a.ts", text="")
    b = SourceFile(path="b.ts", text="")
    assert a.options == {}
    assert b.options == {}
    assert a.options is not b.options


def test_source_file_is_frozen() -> None:
    s = SourceFile(path="a.ts", text="")
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.path = "b.ts"  # type: ignore[misc]


@pytest.mark.parametrize("kind", ["source", "generated"])
def test_source_file_accepts_all_kinds(kind: SourceKind) -> None:
    s = SourceFile(path="a.ts", text="", kind=kind)
    assert s.kind == kind


def test_source_file_generated_with_origin_and_map() -> None:
    s = SourceFile(
        path="App.vel.ts",
        text="export const x = 1;\n",
        origin_path="App.vel",
        source_map='{"version":3,"mappings":""}',
        kind="generated",
    )
    assert s.origin_path == "App.vel"
    assert s.source_map is not None
    assert s.kind == "generated"
