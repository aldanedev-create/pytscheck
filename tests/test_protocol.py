"""Tests for pytscheck.protocol — the tsgo output parser.

Two layers of test:

1. Synthetic input: known shapes fed directly to parse(). This is *not*
   mocking — it is unit-testing the parser's grammar against strings we
   know the parser must accept or reject.
2. Real input: the bundled tsgo is run against a real file, its real
   output is captured, and parse() must reconstruct the expected
   diagnostics. This is the end-to-end check that the parser matches
   the real compiler's format.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pytscheck.exceptions import OutputParseError
from pytscheck.protocol import parse, parse_or_raise


# ---------------------------------------------------------------------------
# Synthetic input (parser grammar)
# ---------------------------------------------------------------------------


def test_parse_empty_output() -> None:
    report = parse("")
    assert report.diagnostics == ()
    assert report.unparsed_lines == ()


def test_parse_whitespace_only() -> None:
    report = parse("   \n\n  \n")
    assert report.diagnostics == ()
    assert report.unparsed_lines == ()


def test_parse_single_error() -> None:
    text = "input.ts(1,7): error TS2322: Type 'string' is not assignable to type 'number'."
    report = parse(text)
    assert len(report.diagnostics) == 1
    d = report.diagnostics[0]
    assert d.file == "input.ts"
    assert d.line == 1
    assert d.column == 7
    assert d.code == 2322
    assert d.category == "error"
    assert "not assignable" in d.message


def test_parse_multiple_errors() -> None:
    text = (
        "a.ts(1,1): error TS1005: ';' expected.\n"
        "b.ts(2,3): error TS2322: Type mismatch.\n"
    )
    report = parse(text)
    assert len(report.diagnostics) == 2
    assert report.diagnostics[0].file == "a.ts"
    assert report.diagnostics[1].file == "b.ts"


def test_parse_warning_category() -> None:
    report = parse("a.ts(1,1): warning TS9999: Deprecated.")
    assert report.diagnostics[0].category == "warning"


def test_parse_suggestion_category() -> None:
    report = parse("a.ts(1,1): suggestion TS9999: Consider renaming.")
    assert report.diagnostics[0].category == "suggestion"


def test_parse_message_category() -> None:
    report = parse("a.ts(1,1): message TS9999: Informational.")
    assert report.diagnostics[0].category == "message"


def test_parse_global_diagnostic() -> None:
    report = parse("error TS18003: No inputs were found in config file.")
    assert len(report.diagnostics) == 1
    d = report.diagnostics[0]
    assert d.file is None
    assert d.code == 18003


def test_parse_multiline_message_continuation() -> None:
    text = (
        "a.ts(1,1): error TS2322: Type 'string' is not assignable to type 'number'.\n"
        "  The expected type comes from property 'age'.\n"
    )
    report = parse(text)
    assert len(report.diagnostics) == 1
    assert "The expected type" in report.diagnostics[0].message


def test_parse_range_position() -> None:
    report = parse("a.ts(1,1-1,5): error TS1005: ';' expected.")
    d = report.diagnostics[0]
    assert d.line == 1
    assert d.column == 1
    assert d.end_line == 1
    assert d.end_column == 5


def test_parse_range_position_multiline() -> None:
    report = parse("a.ts(1,1-3,5): error TS1005: ';' expected.")
    d = report.diagnostics[0]
    assert d.end_line == 3
    assert d.end_column == 5


def test_parse_unparsable_line_is_reported() -> None:
    report = parse("this is not a diagnostic")
    assert report.diagnostics == ()
    assert report.unparsed_lines == ("this is not a diagnostic",)


def test_parse_mixed_valid_and_invalid_lines() -> None:
    text = (
        "a.ts(1,1): error TS1005: ';' expected.\n"
        "this is garbage\n"
        "b.ts(2,1): error TS2322: Type mismatch.\n"
    )
    report = parse(text)
    assert len(report.diagnostics) == 2
    assert report.unparsed_lines == ("this is garbage",)


def test_parse_or_raise_on_unparsable() -> None:
    with pytest.raises(OutputParseError, match="could not parse"):
        parse_or_raise("this is not a diagnostic")


def test_parse_or_raise_with_allow_unparsed() -> None:
    diags = parse_or_raise("this is not a diagnostic", allow_unparsed=True)
    assert diags == ()


def test_parse_or_raise_with_raw_output_attached() -> None:
    try:
        parse_or_raise("garbage line")
    except OutputParseError as e:
        assert e.raw_output == "garbage line"
    else:
        raise AssertionError("expected OutputParseError")


def test_parse_handles_crlf() -> None:
    report = parse("a.ts(1,1): error TS1005: ';' expected.\r\n")
    assert len(report.diagnostics) == 1


def test_parse_handles_path_with_spaces() -> None:
    report = parse("my dir/file.ts(1,1): error TS1005: ';' expected.")
    assert report.diagnostics[0].file == "my dir/file.ts"


def test_parse_handles_path_with_parentheses() -> None:
    # Windows-style and exotic filenames should still parse because the
    # regex is non-greedy and anchors on "(line,col):"
    report = parse("C:/Users/me/My (Project)/a.ts(1,1): error TS1005: ';' expected.")
    assert report.diagnostics[0].file == "C:/Users/me/My (Project)/a.ts"


def test_parse_blank_line_flushes_pending_diagnostic() -> None:
    text = (
        "a.ts(1,1): error TS1005: ';' expected.\n"
        "\n"
        "b.ts(2,1): error TS2322: Type mismatch.\n"
    )
    report = parse(text)
    assert len(report.diagnostics) == 2
    assert report.diagnostics[0].message == "';' expected."


def test_parse_diagnostic_codes_are_ints() -> None:
    report = parse("a.ts(1,1): error TS2322: x")
    assert isinstance(report.diagnostics[0].code, int)
    assert report.diagnostics[0].code == 2322


def test_parse_preserves_message_verbatim() -> None:
    msg = "Type 'a | b' is not assignable to type 'c & d'."
    report = parse(f"a.ts(1,1): error TS2322: {msg}")
    assert report.diagnostics[0].message == msg


def test_parse_multiple_continuation_lines() -> None:
    text = (
        "a.ts(1,1): error TS2322: Type 'string' is not assignable to type 'number'.\n"
        "  The expected type comes from property 'age'.\n"
        "  Which was declared here.\n"
    )
    report = parse(text)
    assert len(report.diagnostics) == 1
    assert "The expected type" in report.diagnostics[0].message
    assert "declared here" in report.diagnostics[0].message


def test_parse_returns_tuple_diagnostics() -> None:
    report = parse("a.ts(1,1): error TS1005: x")
    assert isinstance(report.diagnostics, tuple)
    assert isinstance(report.unparsed_lines, tuple)


# ---------------------------------------------------------------------------
# Real compiler output (requires bundled tsgo)
# ---------------------------------------------------------------------------


def test_parse_real_tsgo_output_for_valid_source(
    tsgo_binary: Path, tmp_path: Path
) -> None:
    f = tmp_path / "ok.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    result = subprocess.run(
        [str(tsgo_binary), "--noEmit", "--strict", str(f)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
    )
    report = parse(result.stdout + result.stderr)
    # A clean check may produce no diagnostics, or the parser may see
    # benign lines we cannot classify. Assert no *errors* were parsed.
    assert not any(d.category == "error" for d in report.diagnostics)


def test_parse_real_tsgo_output_for_type_error(
    tsgo_binary: Path, tmp_path: Path
) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('export const age: number = "twenty";\n', encoding="utf-8")
    result = subprocess.run(
        [str(tsgo_binary), "--noEmit", "--strict", str(f)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
    )
    combined = result.stdout + result.stderr
    report = parse(combined)
    # The real compiler must emit at least one error, and our parser must
    # see it. TS2322 is the canonical "type mismatch" code.
    assert any(d.category == "error" for d in report.diagnostics), combined
    assert any(d.code == 2322 for d in report.diagnostics), [
        (d.code, d.message) for d in report.diagnostics
    ]


def test_parse_real_tsgo_output_for_syntax_error(
    tsgo_binary: Path, tmp_path: Path
) -> None:
    f = tmp_path / "syntax.ts"
    f.write_text("const x: number = ;\n", encoding="utf-8")
    result = subprocess.run(
        [str(tsgo_binary), "--noEmit", str(f)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
    )
    report = parse(result.stdout + result.stderr)
    assert any(d.category == "error" for d in report.diagnostics)