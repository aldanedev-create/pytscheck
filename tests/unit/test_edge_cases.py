"""Unit tests for edge cases that don't fit other files."""

from __future__ import annotations

import pytest

from pytscheck import diagnostics as dg
from pytscheck.config import CompilerOptions
from pytscheck.exceptions import ConfigurationError
from pytscheck.models import Diagnostic, Result
from pytscheck.options import options_to_argv
from pytscheck.paths import normalize
from tests.factories import make_diagnostic

# --- empty inputs ----------------------------------------------------------


def test_sort_empty() -> None:
    assert dg.sort_diagnostics([]) == ()


def test_deduplicate_empty() -> None:
    assert dg.deduplicate([]) == ()


def test_count_empty() -> None:
    assert dg.count_errors([]) == 0
    assert dg.count_warnings([]) == 0


def test_summarize_empty() -> None:
    s = dg.summarize([])
    assert s["total"] == 0
    assert s["files"] == []


def test_group_empty() -> None:
    assert dg.group_by_file([]) == {}


def test_worst_category_empty() -> None:
    assert dg.worst_category([]) is None


# --- very long strings -----------------------------------------------------


def test_very_long_message_preserved() -> None:
    msg = "x" * 10_000
    d = make_diagnostic(message=msg)
    assert d.message == msg
    assert len(d.message) == 10_000


def test_very_long_file_path() -> None:
    path = "a/" * 500 + "b.ts"
    d = make_diagnostic(file=path)
    assert d.file == path


# --- very many diagnostics -------------------------------------------------


def test_many_diagnostics_sort_is_fast() -> None:
    import time

    diags = [
        make_diagnostic(file=f"f{i % 10}.ts", line=i % 1000, code=i % 100) for i in range(5000)
    ]
    start = time.perf_counter()
    ordered = dg.sort_diagnostics(diags)
    elapsed = time.perf_counter() - start
    assert len(ordered) == 5000
    assert elapsed < 2.0


# --- unusual but valid inputs ----------------------------------------------


def test_zero_position_diagnostic() -> None:
    """Global diagnostics may have line=0, column=0."""
    d = make_diagnostic(file=None, line=0, column=0)
    ordered = dg.sort_diagnostics([d])
    assert ordered == (d,)


def test_negative_code_is_not_rejected_by_dataclass() -> None:
    """The dataclass itself does not validate codes; the parser does."""
    d = Diagnostic(file="a.ts", line=1, column=1, code=-1, category="error", message="x")
    assert d.code == -1


def test_category_accepts_all_literals() -> None:
    for cat in ("error", "warning", "suggestion", "message"):
        d = Diagnostic(file="a.ts", line=1, column=1, code=1, category=cat, message="x")
        assert d.category == cat


# --- option edge cases -----------------------------------------------------


def test_options_with_only_extra() -> None:
    argv = options_to_argv(CompilerOptions(strict=False, no_emit=False, extra={"pretty": True}))
    assert argv == ["--pretty"]


def test_options_empty_tuple_flags() -> None:
    argv = options_to_argv(CompilerOptions(types=(), lib=()))
    assert argv.count("--types") == 0
    assert argv.count("--lib") == 0


def test_options_empty_string_values() -> None:
    with pytest.raises(ConfigurationError, match="non-empty string"):
        options_to_argv(CompilerOptions(target="", module=""))


# --- path edge cases -------------------------------------------------------


def test_normalize_dot() -> None:
    p = normalize(".")
    assert p.is_absolute()


def test_normalize_dotdot() -> None:
    p = normalize("..")
    assert p.is_absolute()


def test_normalize_root() -> None:
    p = normalize("/")
    assert str(p) == "/"


def test_normalize_empty_string(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    p = normalize("")
    assert p == tmp_path.resolve()


# --- result edge cases -----------------------------------------------------


def test_result_with_duplicate_diagnostics() -> None:
    d = make_diagnostic()
    r = Result(
        success=False,
        diagnostics=(d, d, d),
        compiler_version="x",
        elapsed_seconds=0.0,
    )
    assert len(r.diagnostics) == 3
    assert len(r.errors) == 3


def test_result_with_negative_elapsed_is_stored() -> None:
    """The dataclass does not validate; callers must not produce negatives."""
    r = Result(
        success=True,
        diagnostics=(),
        compiler_version="x",
        elapsed_seconds=-1.0,
    )
    assert r.elapsed_seconds == -1.0


def test_result_with_empty_compiler_version_is_stored() -> None:
    r = Result(
        success=True,
        diagnostics=(),
        compiler_version="",
        elapsed_seconds=0.0,
    )
    assert r.compiler_version == ""


# --- diagnostics edge cases ------------------------------------------------


def test_deduplicate_keeps_related_information() -> None:
    from pytscheck.models import RelatedInformation

    r = RelatedInformation(file="b.ts", line=1, column=1, message="because")
    a = make_diagnostic(related=(r,))
    b = make_diagnostic(related=(r,))
    assert dg.deduplicate([a, b]) == (a,)


def test_deduplicate_distinguishes_related_differences() -> None:
    from pytscheck.models import RelatedInformation

    r1 = RelatedInformation(file="b.ts", line=1, column=1, message="x")
    r2 = RelatedInformation(file="c.ts", line=1, column=1, message="y")
    a = make_diagnostic(related=(r1,))
    b = make_diagnostic(related=(r2,))
    out = dg.deduplicate([a, b])
    assert len(out) == 2


def test_summarize_handles_global_only() -> None:
    d = make_diagnostic(file=None)
    s = dg.summarize([d])
    assert s["has_global"] is True
    assert s["files"] == []


def test_summarize_files_sorted_and_unique() -> None:
    items = [
        make_diagnostic(file="b.ts"),
        make_diagnostic(file="a.ts"),
        make_diagnostic(file="a.ts"),
    ]
    s = dg.summarize(items)
    assert s["files"] == ["a.ts", "b.ts"]
