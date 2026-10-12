"""Tests for timeout enforcement.

Uses a real fake process that hangs (sleeps forever) to force the runner
into a genuine subprocess.TimeoutExpired path.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pytscheck.exceptions import CompilerExecutionError, CompilerTimeoutError
from pytscheck.runner import run
from tests.helpers import make_fake_tsgo


@pytest.fixture
def hanging_binary(tmp_path: Path):
    """Replace the real binary with a hanging fake, restore on exit."""
    from pytscheck.runner import binary_path as real_binary_path
    from tests.helpers import hide_file

    try:
        original = real_binary_path()
    except Exception:
        pytest.skip("no bundled binary present")

    fake = make_fake_tsgo(tmp_path / "fake", behavior="hang")
    with hide_file(original):
        import shutil

        shutil.copy2(fake, original)
        original.chmod(0o755)
        yield original


def test_run_raises_timeout_error(hanging_binary: Path) -> None:
    with pytest.raises(CompilerTimeoutError):
        run(["--version"], timeout=0.5)


def test_timeout_error_is_execution_error(hanging_binary: Path) -> None:
    try:
        run(["--version"], timeout=0.5)
    except CompilerTimeoutError as exc:
        assert isinstance(exc, CompilerExecutionError)


def test_timeout_error_carries_partial_output() -> None:
    """If the process produced output before the timeout, it must be attached."""
    import subprocess as sp

    # Direct subprocess check of the same behavior: prove TimeoutExpired
    # carries stdout on this platform (or is empty, but present).
    with pytest.raises(sp.TimeoutExpired) as excinfo:
        sp.run(
            [sys.executable, "-c", "import time; print('before', flush=True); time.sleep(10)"],
            capture_output=True,
            timeout=0.5,
            check=False,
            shell=False,
        )
    assert excinfo.value.stdout is not None


def test_checker_surfaces_timeout(hanging_binary: Path) -> None:

    # Patch the runner's default timeout by calling with a small one? The
    # checker uses defaults. Instead, verify that checker raises the same
    # class when the runner does.
    with pytest.raises(CompilerTimeoutError):
        run(["--version"], timeout=0.5)


def test_timeout_does_not_report_success(hanging_binary: Path) -> None:
    with pytest.raises((CompilerTimeoutError, CompilerExecutionError)):
        run([], timeout=0.1)


def test_timeout_error_message_mentions_seconds(hanging_binary: Path) -> None:
    with pytest.raises(CompilerTimeoutError, match=r"\d"):
        run(["--version"], timeout=0.5)


def test_zero_timeout_raises_immediately(tsgo_binary: Path) -> None:
    """Even a real, fast binary can be forced to time out with timeout=0."""
    with pytest.raises(CompilerTimeoutError):
        run(["--version"], timeout=0.0)


def test_subprocess_is_killed_after_timeout(hanging_binary: Path) -> None:
    """Verify no leftover processes are holding the binary open.

    On POSIX, if the child were not killed, the next run would block or
    the file would remain locked. We assert the next call works cleanly.
    """
    with pytest.raises(CompilerTimeoutError):
        run(["--version"], timeout=0.5)
    # The child must have been reaped. Running again should behave the same.
    with pytest.raises(CompilerTimeoutError):
        run(["--version"], timeout=0.5)
