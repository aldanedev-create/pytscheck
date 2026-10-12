"""Unit tests for deterministic diagnostic ordering.

The ordering is defined in pytscheck.diagnostics.sort_diagnostics. Every
Result produced by the library contains diagnostics in that order.
"""

from __future__ import annotations

from pytscheck.diagnostics import sort_diagnostics
from tests.factories import make_diagnostic


def _d(**kw):
    return make_diagnostic(**kw)


# --- primary sort key: file -------------------------------------------------


def test_global_diagnostics_last() -> None:
    diags = [_d(file=None, line=0), _d(file="a.ts", line=1)]
    assert [d.file for d in sort_diagnostics(diags)] == ["a.ts", None]


def test_files_sorted_alphabetically() -> None:
    diags = [_d(file="c.ts"), _d(file="a.ts"), _d(file="b.ts")]
    assert [d.file for d in sort_diagnostics(diags)] == ["a.ts", "b.ts", "c.ts"]


def test_files_case_sensitive_sort() -> None:
    diags = [_d(file="B.ts"), _d(file="a.ts"), _d(file="A.ts")]
    # Python's str ordering puts uppercase before lowercase
    assert [d.file for d in sort_diagnostics(diags)] == ["A.ts", "B.ts", "a.ts"]


# --- secondary sort key: line ----------------------------------------------


def test_lines_sorted_within_file() -> None:
    diags = [
        _d(file="a.ts", line=5),
        _d(file="a.ts", line=1),
        _d(file="a.ts", line=3),
    ]
    assert [d.line for d in sort_diagnostics(diags)] == [1, 3, 5]


# --- tertiary sort key: column ---------------------------------------------


def test_columns_sorted_within_line() -> None:
    diags = [
        _d(file="a.ts", line=1, column=5),
        _d(file="a.ts", line=1, column=1),
        _d(file="a.ts", line=1, column=3),
    ]
    assert [d.column for d in sort_diagnostics(diags)] == [1, 3, 5]


# --- quaternary sort key: code ---------------------------------------------


def test_codes_sorted_within_position() -> None:
    diags = [
        _d(file="a.ts", line=1, column=1, code=2000),
        _d(file="a.ts", line=1, column=1, code=1000),
    ]
    assert [d.code for d in sort_diagnostics(diags)] == [1000, 2000]


# --- final tiebreaker: message ---------------------------------------------


def test_messages_sorted_when_all_else_equal() -> None:
    diags = [
        _d(file="a.ts", line=1, column=1, code=1000, message="z"),
        _d(file="a.ts", line=1, column=1, code=1000, message="a"),
    ]
    assert [d.message for d in sort_diagnostics(diags)] == ["a", "z"]


# --- stability --------------------------------------------------------------


def test_same_input_same_output() -> None:
    diags = [_d(file="a.ts"), _d(file="b.ts"), _d(file=None)]
    assert sort_diagnostics(diags) == sort_diagnostics(diags)


def test_returns_tuple() -> None:
    assert isinstance(sort_diagnostics([_d()]), tuple)


def test_empty_input() -> None:
    assert sort_diagnostics([]) == ()


def test_identical_diagnostics_kept() -> None:
    d = _d()
    result = sort_diagnostics([d, d, d])
    assert len(result) == 3
    assert result[0] == result[1] == result[2]


# --- full ordering interaction ----------------------------------------------


def test_full_ordering_interaction() -> None:
    diags = [
        _d(file="b.ts", line=1, column=1, code=1000, message="x"),
        _d(file="a.ts", line=2, column=1, code=1000, message="x"),
        _d(file="a.ts", line=1, column=5, code=1000, message="x"),
        _d(file="a.ts", line=1, column=1, code=2000, message="x"),
        _d(file="a.ts", line=1, column=1, code=1000, message="y"),
        _d(file="a.ts", line=1, column=1, code=1000, message="x"),
        _d(file=None, line=0, column=0, code=1000, message="x"),
    ]
    ordered = sort_diagnostics(diags)
    expected = [
        ("a.ts", 1, 1, 1000, "x"),
        ("a.ts", 1, 1, 1000, "y"),
        ("a.ts", 1, 1, 2000, "x"),
        ("a.ts", 1, 5, 1000, "x"),
        ("a.ts", 2, 1, 1000, "x"),
        ("b.ts", 1, 1, 1000, "x"),
        (None, 0, 0, 1000, "x"),
    ]
    actual = [(d.file, d.line, d.column, d.code, d.message) for d in ordered]
    assert actual == expected
