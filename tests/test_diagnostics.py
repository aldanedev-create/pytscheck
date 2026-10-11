"""Tests for pytscheck.diagnostics."""

from __future__ import annotations

from pytscheck import diagnostics as dg
from pytscheck.models import Diagnostic, RelatedInformation


def _d(
    file: str | None = "a.ts",
    line: int = 1,
    column: int = 1,
    code: int = 2322,
    category: str = "error",
    message: str = "m",
) -> Diagnostic:
    return Diagnostic(
        file=file,
        line=line,
        column=column,
        code=code,
        category=category,  # type: ignore[arg-type]
        message=message,
    )


# --- sort_diagnostics -------------------------------------------------------


def test_sort_empty() -> None:
    assert dg.sort_diagnostics([]) == ()


def test_sort_by_file_then_position() -> None:
    items = [
        _d(file="b.ts", line=1),
        _d(file="a.ts", line=5),
        _d(file="a.ts", line=1),
        _d(file=None, line=0),
    ]
    out = dg.sort_diagnostics(items)
    assert [x.file for x in out] == ["a.ts", "a.ts", "b.ts", None]
    assert [x.line for x in out[:3]] == [1, 5, 1]


def test_sort_by_column_then_code() -> None:
    items = [
        _d(line=1, column=5, code=2000),
        _d(line=1, column=5, code=1000),
        _d(line=1, column=1, code=9999),
    ]
    out = dg.sort_diagnostics(items)
    assert [(x.column, x.code) for x in out] == [(1, 9999), (5, 1000), (5, 2000)]


def test_sort_is_deterministic() -> None:
    items = [_d(file="a.ts", line=1), _d(file="a.ts", line=1)]
    assert dg.sort_diagnostics(items) == dg.sort_diagnostics(items)


def test_sort_returns_tuple() -> None:
    assert isinstance(dg.sort_diagnostics([_d()]), tuple)


# --- deduplicate ------------------------------------------------------------


def test_deduplicate_removes_exact_duplicates() -> None:
    a = _d(message="x")
    b = _d(message="x")
    c = _d(message="y")
    assert dg.deduplicate([a, b, c]) == (a, c)


def test_deduplicate_preserves_first_occurrence_order() -> None:
    a = _d(message="a")
    b = _d(message="b")
    assert dg.deduplicate([a, b, a, b]) == (a, b)


def test_deduplicate_keeps_near_duplicates() -> None:
    a = _d(message="x", line=1)
    b = _d(message="x", line=2)
    assert dg.deduplicate([a, b]) == (a, b)


# --- filters ----------------------------------------------------------------


def test_filter_by_category() -> None:
    items = [_d(category="error"), _d(category="warning"), _d(category="suggestion")]
    assert len(dg.filter_by_category(items, "error")) == 1
    assert len(dg.filter_by_category(items, "warning")) == 1
    assert len(dg.filter_by_category(items, "suggestion")) == 1
    assert len(dg.filter_by_category(items, "message")) == 0


def test_filter_by_file() -> None:
    items = [_d(file="a.ts"), _d(file="b.ts"), _d(file=None)]
    assert len(dg.filter_by_file(items, "a.ts")) == 1
    assert len(dg.filter_by_file(items, "c.ts")) == 0


def test_filter_by_code() -> None:
    items = [_d(code=1000), _d(code=2322), _d(code=2322)]
    assert len(dg.filter_by_code(items, 2322)) == 2
    assert len(dg.filter_by_code(items, 9999)) == 0


# --- counts -----------------------------------------------------------------


def test_count_errors_warnings() -> None:
    items = [_d(category="error"), _d(category="error"), _d(category="warning")]
    assert dg.count_errors(items) == 2
    assert dg.count_warnings(items) == 1


def test_count_by_category() -> None:
    items = [_d(category="error"), _d(category="warning"), _d(category="warning")]
    assert dg.count_by_category(items) == {"error": 1, "warning": 2}


def test_count_by_category_empty() -> None:
    assert dg.count_by_category([]) == {}


def test_has_errors() -> None:
    assert dg.has_errors([_d(category="error")]) is True
    assert dg.has_errors([_d(category="warning")]) is False
    assert dg.has_errors([]) is False


def test_worst_category() -> None:
    assert dg.worst_category([]) is None
    assert dg.worst_category([_d(category="message")]) == "message"
    assert dg.worst_category([_d(category="message"), _d(category="warning")]) == "warning"
    assert dg.worst_category([_d(category="warning"), _d(category="error")]) == "error"


# --- grouping ---------------------------------------------------------------


def test_group_by_file() -> None:
    items = [_d(file="a.ts"), _d(file="a.ts"), _d(file=None)]
    groups = dg.group_by_file(items)
    assert set(groups) == {"a.ts", None}
    assert len(groups["a.ts"]) == 2


def test_group_by_file_empty() -> None:
    assert dg.group_by_file([]) == {}


# --- summarize --------------------------------------------------------------


def test_summarize_shape() -> None:
    items = [
        _d(file="a.ts", category="error"),
        _d(file="b.ts", category="warning"),
        _d(file=None, category="error"),
    ]
    s = dg.summarize(items)
    assert s["total"] == 3
    assert s["errors"] == 2
    assert s["warnings"] == 1
    assert s["by_category"] == {"error": 2, "warning": 1}
    assert s["files"] == ["a.ts", "b.ts"]
    assert s["has_global"] is True


def test_summarize_empty() -> None:
    s = dg.summarize([])
    assert s["total"] == 0
    assert s["errors"] == 0
    assert s["warnings"] == 0
    assert s["files"] == []
    assert s["has_global"] is False


# --- constructors -----------------------------------------------------------


def test_make_related() -> None:
    r = dg.make_related("b.ts", 5, 3, "because")
    assert isinstance(r, RelatedInformation)
    assert r.file == "b.ts"
    assert r.line == 5
    assert r.column == 3
    assert r.message == "because"


# --- iterators --------------------------------------------------------------


def test_iter_errors() -> None:
    items = [_d(category="error"), _d(category="warning"), _d(category="error")]
    assert len(list(dg.iter_errors(items))) == 2


def test_iter_warnings() -> None:
    items = [_d(category="error"), _d(category="warning")]
    assert len(list(dg.iter_warnings(items))) == 1


# --- integration with real Result -------------------------------------------


def test_diagnostics_helpers_on_real_result_type() -> None:
    from pytscheck.results import build_result

    items = [_d(file="a.ts", category="error"), _d(file="a.ts", category="warning")]
    r = build_result(items, compiler_version="7.0.0", elapsed_seconds=0.01)
    assert dg.count_errors(r.diagnostics) == 1
    assert dg.has_errors(r.diagnostics)
    assert dg.worst_category(r.diagnostics) == "error"