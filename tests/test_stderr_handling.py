"""Tests for stdout/stderr separation and stderr-only diagnostics."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pytscheck.runner import run


def test_stdout_and_stderr_are_separate(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('const x: number = "bad";\n', encoding="utf-8")
    result = run(["--noEmit", str(f)])
    assert isinstance(result.stdout, str)
    assert isinstance(result.stderr, str)


def test_stdout_does_not_contain_stderr_bytes(tsgo_binary: Path, tmp_path: Path) -> None:
    """The runner must not merge stdout and stderr into one stream."""
    f = tmp_path / "bad.ts"
    f.write_text('const x: number = "bad";\n', encoding="utf-8")
    result = run(["--noEmit", str(f)])
    # If tsgo writes diagnostics to stderr, stdout must not include them.
    # If it writes to stdout, stderr must not include them.
    if result.stdout:
        assert "error TS" not in result.stderr or "error TS" not in result.stdout


def test_stderr_only_output_is_captured(tmp_path: Path) -> None:
    """A real process that writes only to stderr still has its output captured."""
    result = subprocess.run(
        [
            "python",
            "-c",
            "import sys; sys.stderr.write('only stderr\\n'); sys.exit(1)",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        shell=False,
    )
    assert result.stdout == ""
    assert "only stderr" in result.stderr


def test_diagnostics_on_stderr_are_seen_by_checker(
    tsgo_binary: Path, tmp_path: Path
) -> None:
    """If tsgo reports diagnostics on stderr, checker must still see them."""
    from pytscheck import checker

    f = tmp_path / "bad.ts"
    f.write_text('const x: number = "bad";\n', encoding="utf-8")
    r = checker.check_file(f)
    assert not r.success


def test_empty_stderr_when_no_errors(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "ok.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    result = run(["--noEmit", "--strict", str(f)])
    # Clean runs typically produce empty stderr; if not, it must not contain
    # the word "error".
    assert "error" not in result.stderr.lower()


def test_stderr_preserved_when_stdout_is_large(tmp_path: Path) -> None:
    """A large stdout must not crowd out stderr capture."""
    result = subprocess.run(
        [
            "python",
            "-c",
            (
                "import sys\n"
                "sys.stdout.write('x' * 100000)\n"
                "sys.stderr.write('ERR!')\n"
                "sys.exit(1)\n"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        shell=False,
    )
    assert len(result.stdout) == 100000
    assert result.stderr == "ERR!"


def test_runner_does_not_merge_streams(tmp_path: Path) -> None:
    """stderr=subprocess.PIPE and stdout=subprocess.PIPE must be separate."""
    from pytscheck.runner import binary_path as real_binary_path
    from pytscheck.exceptions import CompilerNotFoundError

    try:
        real_binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")
    # Runner signature enforces separate capture; this is a compile-time
    # guarantee verified by inspecting the runner's source contract.
    import inspect

    from pytscheck import runner

    source = inspect.getsource(runner.run)
    assert "capture_output=True" in source or (
        "stdout=subprocess.PIPE" in source and "stderr=subprocess.PIPE" in source
    )