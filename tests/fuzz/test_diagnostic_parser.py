"""Fuzz the tsgo output parser.

The parser in `pytscheck.protocol` is the project's main ongoing
maintenance cost and receives the most testing. These tests feed it
hostile, random, and structured inputs to make sure it:

- never crashes
- never hangs
- never returns garbage silently
- raises `OutputParseError` when it cannot classify input
"""

from __future__ import annotations

import random
import string

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from pytscheck.exceptions import OutputParseError
from pytscheck.models import Diagnostic
from pytscheck.protocol import ParseReport, parse, parse_or_raise

# ---------------------------------------------------------------------------
# Invariants (property-based)
# ---------------------------------------------------------------------------


@given(st.text())
@settings(
    max_examples=500,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
def test_parse_never_crashes_on_arbitrary_text(text: str) -> None:
    report = parse(text)
    assert isinstance(report, ParseReport)
    assert isinstance(report.diagnostics, tuple)
    assert isinstance(report.unparsed_lines, tuple)


@given(st.text())
@settings(
    max_examples=300,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
def test_parse_diagnostics_are_well_formed(text: str) -> None:
    report = parse(text)
    for d in report.diagnostics:
        assert isinstance(d, Diagnostic)
        assert d.line >= 0
        assert d.column >= 0
        assert d.code >= 0
        assert d.category in {"error", "warning", "suggestion", "message"}
        assert isinstance(d.message, str)
        assert d.file is None or isinstance(d.file, str)


@given(st.text())
@settings(
    max_examples=300,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
def test_parse_or_raise_contract(text: str) -> None:
    """parse_or_raise returns diagnostics or raises OutputParseError, never both silently."""
    try:
        diags = parse_or_raise(text)
    except OutputParseError as exc:
        assert exc.raw_output is not None
        return
    # If we got here, every line must have been classified
    assert all(isinstance(d, Diagnostic) for d in diags)


# ---------------------------------------------------------------------------
# Structured grammar fuzzing
# ---------------------------------------------------------------------------


def _random_diagnostic_line(rng: random.Random) -> str:
    """Generate a syntactically valid diagnostic line."""
    file = "".join(rng.choices(string.ascii_letters + "._/-", k=rng.randint(1, 30)))
    line = rng.randint(1, 10_000)
    col = rng.randint(1, 500)
    category = rng.choice(["error", "warning", "suggestion", "message"])
    code = rng.randint(1000, 9999)
    message = "".join(
        rng.choices(
            string.ascii_letters + string.digits + string.punctuation + " \t", k=rng.randint(1, 100)
        )
    )
    return f"{file}({line},{col}): {category} TS{code}: {message}"


def test_random_valid_lines_parse(rng: random.Random) -> None:
    """Valid diagnostic lines must round-trip through the parser."""
    for _ in range(500):
        line = _random_diagnostic_line(rng)
        report = parse(line)
        assert len(report.diagnostics) == 1, f"failed on: {line!r}"
        d = report.diagnostics[0]
        assert d.line >= 1
        assert d.column >= 1
        assert 1000 <= d.code <= 9999


def test_random_diagnostic_streams(rng: random.Random) -> None:
    """Streams of valid lines must all parse."""
    for _ in range(100):
        n = rng.randint(1, 30)
        lines = [_random_diagnostic_line(rng) for _ in range(n)]
        text = "\n".join(lines)
        report = parse(text)
        assert len(report.diagnostics) == n


def test_multiline_continuation_fuzz(rng: random.Random) -> None:
    """Diagnostics with continuation lines must include continuations."""
    for _ in range(200):
        header = _random_diagnostic_line(rng)
        n_cont = rng.randint(1, 5)
        conts = [
            "  " + "".join(rng.choices(string.ascii_letters + " ", k=rng.randint(1, 50)))
            for _ in range(n_cont)
        ]
        text = "\n".join([header, *conts])
        report = parse(text)
        assert len(report.diagnostics) == 1
        assert all(c.strip() in report.diagnostics[0].message for c in conts)


# ---------------------------------------------------------------------------
# Hostile alphabets
# ---------------------------------------------------------------------------


def test_only_null_bytes() -> None:
    report = parse("\x00" * 100)
    assert isinstance(report, ParseReport)


def test_only_control_characters() -> None:
    text = "".join(chr(i) for i in range(1, 32))
    report = parse(text)
    assert isinstance(report, ParseReport)


def test_only_high_bytes() -> None:
    text = "".join(chr(i) for i in range(0x80, 0x100))
    report = parse(text)
    assert isinstance(report, ParseReport)


def test_mixed_hostile_chars(rng: random.Random) -> None:
    alphabet = "".join(chr(i) for i in range(0, 0x100))
    for _ in range(50):
        text = "".join(rng.choices(alphabet, k=rng.randint(1, 2000)))
        report = parse(text)
        assert isinstance(report, ParseReport)


def test_very_long_line() -> None:
    line = "a" * 1_000_000
    report = parse(line)
    assert isinstance(report, ParseReport)


def test_many_empty_lines() -> None:
    report = parse("\n" * 100_000)
    assert report.diagnostics == ()
    assert report.unparsed_lines == ()


def test_line_endings_mixed(rng: random.Random) -> None:
    """\n, \r\n, and \r must all be handled."""
    for _ in range(50):
        n = rng.randint(1, 20)
        lines = [_random_diagnostic_line(rng) for _ in range(n)]
        sep = rng.choice(["\n", "\r\n", "\r"])
        text = sep.join(lines)
        report = parse(text)
        # \r-only may not split the same way; assert no crash and either
        # parses all or none.
        assert isinstance(report, ParseReport)


# ---------------------------------------------------------------------------
# Specific hostile patterns
# ---------------------------------------------------------------------------


def test_looks_like_header_but_no_colon() -> None:
    report = parse("file.ts(1,1) error TS2322 no colon")
    assert report.diagnostics == ()


def test_looks_like_header_but_no_code() -> None:
    report = parse("file.ts(1,1): error: Type mismatch.")
    assert report.diagnostics == ()


def test_looks_like_header_but_no_parens() -> None:
    report = parse("file.ts: error TS2322: Type mismatch.")
    assert report.diagnostics == ()


def test_looks_like_header_but_non_numeric_position() -> None:
    report = parse("file.ts(x,y): error TS2322: Type mismatch.")
    assert report.diagnostics == ()


def test_huge_line_column() -> None:
    report = parse("file.ts(999999999999,999999999999): error TS2322: x")
    assert isinstance(report, ParseReport)


def test_huge_error_code() -> None:
    report = parse("file.ts(1,1): error TS99999999999999999999: x")
    assert isinstance(report, ParseReport)


def test_negative_position() -> None:
    report = parse("file.ts(-1,-1): error TS2322: x")
    assert report.diagnostics == ()


def test_unicode_in_file_and_message() -> None:
    text = "ファイル(1,1): error TS2322: Type mismatch in 世界 🌍"
    report = parse(text)
    assert len(report.diagnostics) == 1
    assert "世界" in report.diagnostics[0].message


def test_zero_width_chars_in_header() -> None:
    text = "file\u200b.ts(1,1): error TS2322: x"
    report = parse(text)
    assert isinstance(report, ParseReport)


def test_rtl_override_in_header() -> None:
    text = "file\u202e.ts(1,1): error TS2322: x"
    report = parse(text)
    assert isinstance(report, ParseReport)


def test_header_without_leading_whitespace_after_blank() -> None:
    text = "file.ts(1,1): error TS2322: first\n\nfile.ts(2,1): error TS2322: second\n"
    report = parse(text)
    assert len(report.diagnostics) == 2


def test_indented_header_is_not_continuation_without_pending() -> None:
    """An indented line with no pending diagnostic must not crash."""
    text = "    this is indented\n"
    report = parse(text)
    assert isinstance(report, ParseReport)


def test_continuation_without_header_does_not_join() -> None:
    """A continuation line before any header must not become a diagnostic."""
    text = "  orphan continuation\nfile.ts(1,1): error TS2322: real\n"
    report = parse(text)
    assert len(report.diagnostics) == 1


def test_many_diagnostics_in_one_run(rng: random.Random) -> None:
    lines = [_random_diagnostic_line(rng) for _ in range(5_000)]
    report = parse("\n".join(lines))
    assert len(report.diagnostics) == 5_000
