"""Tests that stdout parsing matches the runner's protocol contract.

The runner's contract: stdout carries the compiler's machine-facing output;
stderr carries warnings and messages; the parser consumes both.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pytscheck.protocol import parse
from pytscheck.runner import run


def test_runner_returns_string_stdout(tsgo_binary: Path) -> None:
    result = run(["--version"])
    assert isinstance(result.stdout, str)


def test_runner_returns_string_stderr(tsgo_binary: Path) -> None:
    result = run(["--version"])
    assert isinstance(result.stderr, str)


def test_real_output_parses_as_diagnostics(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('const age: number = "twenty";\n', encoding="utf-8")
    result = run(["--noEmit", "--strict", str(f)])
    combined = result.stdout + "\n" + result.stderr
    report = parse(combined)
    assert any(d.category == "error" for d in report.diagnostics), combined


def test_real_output_contains_ts_error_code(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('const age: number = "twenty";\n', encoding="utf-8")
    result = run(["--noEmit", "--strict", str(f)])
    combined = result.stdout + result.stderr
    assert "TS2322" in combined


def test_real_output_line_and_column_are_positive(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('const age: number = "twenty";\n', encoding="utf-8")
    result = run(["--noEmit", "--strict", str(f)])
    report = parse(result.stdout + "\n" + result.stderr)
    errors = [d for d in report.diagnostics if d.category == "error"]
    assert errors
    for d in errors:
        assert d.line >= 1
        assert d.column >= 1


def test_protocol_handles_empty_combined_output(tmp_path: Path) -> None:
    report = parse("")
    assert report.diagnostics == ()


def test_protocol_handles_only_whitespace(tmp_path: Path) -> None:
    report = parse("   \n\n")
    assert report.diagnostics == ()


def test_protocol_output_is_deterministic(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('const age: number = "twenty";\n', encoding="utf-8")
    r1 = run(["--noEmit", "--strict", str(f)])
    r2 = run(["--noEmit", "--strict", str(f)])
    report1 = parse(r1.stdout + "\n" + r1.stderr)
    report2 = parse(r2.stdout + "\n" + r2.stderr)
    # Same compiler, same input: same diagnostics (in the same order).
    assert report1.diagnostics == report2.diagnostics


def test_subprocess_produces_expected_stdout_pipe(tmp_path: Path) -> None:
    """Directly verify subprocess behavior matches what the runner relies on."""
    result = subprocess.run(
        [
            "python",
            "-c",
            (
                "import sys\n"
                "sys.stdout.write('STDOUT\\n')\n"
                "sys.stderr.write('STDERR\\n')\n"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        shell=False,
    )
    assert "STDOUT" in result.stdout
    assert "STDERR" in result.stderr
    assert "STDERR" not in result.stdout
    assert "STDOUT" not in result.stderr


def test_cli_json_output_is_valid_json(tsgo_binary: Path, tmp_path: Path) -> None:
    from tests.helpers import parse_cli_json, run_cli

    f = tmp_path / "bad.ts"
    f.write_text('const age: number = "twenty";\n', encoding="utf-8")
    code, out, _ = run_cli(["file", str(f), "--json"])
    payload = parse_cli_json(out)
    assert "diagnostics" in payload
    assert isinstance(payload["diagnostics"], list)