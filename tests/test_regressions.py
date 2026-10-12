"""Regression tests for behavior that must not change.

Each test here corresponds to a bug that was found and fixed, or a
behavioral contract we are choosing to freeze. If a future change makes
any of these fail, that change is a regression and must be justified.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import checker
from pytscheck.protocol import parse

# --- parser behavior --------------------------------------------------------


def test_regression_multiline_message_contination_preserved() -> None:
    """A diagnostic whose message spans lines must include the continuation."""
    text = (
        "a.ts(1,1): error TS2322: Type 'string' is not assignable to type 'number'.\n"
        "  The expected type comes from property 'age'.\n"
    )
    report = parse(text)
    assert len(report.diagnostics) == 1
    assert "The expected type" in report.diagnostics[0].message


def test_regression_blank_line_flushes_diagnostic() -> None:
    """A blank line between diagnostics must not merge them."""
    text = "a.ts(1,1): error TS1005: ';' expected.\n\nb.ts(2,1): error TS2322: Type mismatch.\n"
    report = parse(text)
    assert len(report.diagnostics) == 2


def test_regression_path_with_parens() -> None:
    """Paths containing parentheses must still parse."""
    text = "C:/Users/me/My (Project)/a.ts(1,1): error TS1005: ';' expected."
    report = parse(text)
    assert report.diagnostics[0].file == "C:/Users/me/My (Project)/a.ts"


def test_regression_path_with_spaces() -> None:
    text = "my project/a.ts(1,1): error TS1005: ';' expected."
    report = parse(text)
    assert report.diagnostics[0].file == "my project/a.ts"


def test_regression_crlf_lines() -> None:
    text = "a.ts(1,1): error TS1005: ';' expected.\r\n"
    report = parse(text)
    assert len(report.diagnostics) == 1


# --- ordering ---------------------------------------------------------------


def test_regression_diagnostic_order_is_deterministic(tsgo_binary: Path) -> None:
    """Same input, same order, run after run."""
    src = (
        'export const a: number = "x";\n'
        'export const b: number = "y";\n'
        'export const c: number = "z";\n'
    )
    r1 = checker.check_source(src)
    r2 = checker.check_source(src)
    assert [(d.line, d.code) for d in r1.errors] == [(d.line, d.code) for d in r2.errors]


# --- error taxonomy --------------------------------------------------------


def test_regression_extraction_error_is_not_a_type_error() -> None:
    """Adapter extraction failures must be AdapterExtractionError, not diagnostics."""
    from pytscheck.exceptions import AdapterError, AdapterExtractionError, PyTSCheckError

    assert issubclass(AdapterExtractionError, AdapterError)
    assert issubclass(AdapterExtractionError, PyTSCheckError)
    # And it must not be a Diagnostic
    from pytscheck.models import Diagnostic

    assert not issubclass(AdapterExtractionError, Diagnostic)


def test_regression_timeout_is_execution_error() -> None:
    from pytscheck.exceptions import CompilerExecutionError, CompilerTimeoutError

    assert issubclass(CompilerTimeoutError, CompilerExecutionError)


# --- API stability ----------------------------------------------------------


def test_regression_check_source_does_not_require_file() -> None:
    """`check` accepts a string; it must not require a path."""
    from pytscheck.api import check

    # Validation-only: source with a NUL byte is rejected before any compiler
    from pytscheck.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError):
        check("a\x00b")


def test_regression_api_rejects_filename_with_separator() -> None:
    from pytscheck.api import check
    from pytscheck.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError, match="basename"):
        check("const x = 1;", filename="dir/file.ts")


# --- source handling --------------------------------------------------------


def test_regression_unicode_source(tsgo_binary: Path) -> None:
    src = 'export const s: string = "héllo 世界 🌍";'
    r = checker.check_source(src)
    assert r.success


def test_regression_empty_source_is_valid(tsgo_binary: Path) -> None:
    """An empty source file is valid TypeScript."""
    r = checker.check_source("")
    assert r.success


def test_regression_whitespace_only_source(tsgo_binary: Path) -> None:
    r = checker.check_source("   \n\n   ")
    assert r.success


def test_regression_comment_only_source(tsgo_binary: Path) -> None:
    r = checker.check_source("// a comment only\n")
    assert r.success


# --- error code stability ---------------------------------------------------


def test_regression_ts2322_code_stable(tsgo_binary: Path) -> None:
    src = 'const x: number = "s";'
    r = checker.check_source(src)
    assert any(d.code == 2322 for d in r.errors)


def test_regression_ts1005_code_stable(tsgo_binary: Path) -> None:
    src = "const x: number = ;"
    r = checker.check_source(src)
    assert any(d.code == 1005 for d in r.errors), [(d.code, d.message) for d in r.errors]


# --- no-emit behavior --------------------------------------------------------


def test_regression_no_emit_by_default(tsgo_binary: Path, tmp_path: Path) -> None:
    """The checker must never produce .js output next to a source file."""
    f = tmp_path / "input.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    checker.check_file(f)
    siblings = {p.name for p in tmp_path.iterdir()}
    assert "input.js" not in siblings
    assert "input.js.map" not in siblings
    assert "input.d.ts" not in siblings


# --- idempotency ------------------------------------------------------------


def test_regression_repeated_checks_do_not_leak_files(tsgo_binary: Path, tmp_path: Path) -> None:
    before = set(tmp_path.iterdir())
    for _ in range(3):
        checker.check_source("export const x: number = 1;")
    after = set(tmp_path.iterdir())
    assert before == after


def test_regression_result_is_hashable(tsgo_binary: Path) -> None:
    r = checker.check_source("export const x: number = 1;")
    assert hash(r) == hash(r)
