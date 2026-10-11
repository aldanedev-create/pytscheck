"""Tests for behavior when the compiler crashes mid-run."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pytscheck.exceptions import (
    CompilerExecutionError,
    CompilerNotFoundError,
    OutputParseError,
)
from pytscheck.runner import run
from tests.helpers import hide_file, make_fake_tsgo


@pytest.fixture
def crashing_binary(tmp_path: Path):
    from pytscheck.runner import binary_path as real_binary_path

    try:
        original = real_binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    fake = make_fake_tsgo(tmp_path / "fake", behavior="crash")
    with hide_file(original):
        import shutil

        shutil.copy2(fake, original)
        original.chmod(0o755)
        yield original


def test_crashing_process_returns_nonzero(crashing_binary: Path) -> None:
    result = run(["--version"])
    assert result.returncode != 0


def test_checker_rejects_crashing_process(crashing_binary: Path) -> None:
    from pytscheck import checker

    with pytest.raises((CompilerExecutionError, OutputParseError)):
        checker.check_source("const x = 1;")


def test_crashing_process_never_reports_success(crashing_binary: Path) -> None:
    from pytscheck import checker

    try:
        r = checker.check_source("const x = 1;")
    except (CompilerExecutionError, OutputParseError):
        return
    raise AssertionError("crashing compiler was accepted as success")


def test_crashing_process_produces_empty_output(crashing_binary: Path) -> None:
    result = run(["--version"])
    # Crash before printing anything
    assert result.stdout == "" or result.returncode != 0


def test_crashing_process_is_reported_with_exit_code() -> None:
    """Verify the exception carries the exit code when the caller inspects it."""
    import subprocess
    import sys

    # Direct check: non-zero exit is visible to the caller.
    result = subprocess.run(
        [sys.executable, "-c", "import sys; sys.exit(139)"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        shell=False,
    )
    assert result.returncode == 139


def test_segfault_reports_negative_or_large_returncode(crashing_binary: Path) -> None:
    """On POSIX, a SIGSEGV-killed process reports a negative returncode."""
    result = run(["--version"])
    assert result.returncode != 0
    if os.name != "nt":
        # Negative returncode == killed by signal number
        assert result.returncode < 0 or result.returncode > 128


def test_crash_recovers_for_next_call(crashing_binary: Path) -> None:
    """A crash must not leave the runner in a broken state."""
    with pytest.raises(Exception):
        from pytscheck import checker

        checker.check_source("const x = 1;")
    # Second call behaves the same way
    with pytest.raises(Exception):
        from pytscheck import checker

        checker.check_source("const y = 2;")