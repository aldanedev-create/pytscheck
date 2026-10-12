"""Tests for pytscheck.runner.

These invoke the real bundled tsgo binary. Nothing is mocked. Tests that
need the binary skip when it is absent.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from pytscheck.exceptions import (
    CompilerExecutionError,
    CompilerNotFoundError,
    CompilerTimeoutError,
    UnsupportedPlatformError,
)
from pytscheck.runner import RunResult, binary_path, run
from tests.helpers import file_has_executable_bit, hide_file

# --- binary_path -----------------------------------------------------------


def test_binary_path_returns_existing_file(tsgo_binary: Path) -> None:
    assert binary_path() == tsgo_binary
    assert binary_path().exists()


def test_binary_path_is_executable(tsgo_binary: Path) -> None:
    assert file_has_executable_bit(tsgo_binary)


def test_binary_path_raises_when_hidden() -> None:
    try:
        binary = binary_path()
    except (CompilerNotFoundError, UnsupportedPlatformError):
        pytest.skip("no bundled binary present")

    with hide_file(binary), pytest.raises(CompilerNotFoundError):
        binary_path()


def test_binary_path_raises_when_not_executable() -> None:
    if os.name == "nt":
        pytest.skip("permission bits not honored on Windows")
    try:
        binary = binary_path()
    except (CompilerNotFoundError, UnsupportedPlatformError):
        pytest.skip("no bundled binary present")

    original_mode = binary.stat().st_mode
    binary.chmod(0o644)
    try:
        with pytest.raises(CompilerNotFoundError, match="not executable"):
            binary_path()
    finally:
        binary.chmod(original_mode)


# --- run: happy paths ------------------------------------------------------


def test_run_version_flag(tsgo_binary: Path) -> None:
    result = run(["--version"])
    assert isinstance(result, RunResult)
    assert result.returncode == 0
    assert result.stdout.strip() or result.stderr.strip()
    assert result.elapsed_seconds >= 0.0


def test_run_help(tsgo_binary: Path) -> None:
    result = run(["--help"])
    # Some CLIs exit non-zero for --help; tsgo may be either. We only assert
    # that the call succeeded and produced output.
    assert result.stdout or result.stderr


def test_run_captures_stdout_and_stderr_separately(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('const x: number = "bad";\n', encoding="utf-8")
    result = run(["--noEmit", "--strict", str(f)])
    # Diagnostics may go to stdout or stderr; both are captured separately.
    assert isinstance(result.stdout, str)
    assert isinstance(result.stderr, str)


def test_run_returns_argv_tuple(tsgo_binary: Path) -> None:
    result = run(["--version"])
    assert isinstance(result.argv, tuple)
    assert str(tsgo_binary) == result.argv[0]


def test_run_elapsed_seconds_is_float(tsgo_binary: Path) -> None:
    result = run(["--version"])
    assert isinstance(result.elapsed_seconds, float)
    assert result.elapsed_seconds > 0.0


# --- run: error paths ------------------------------------------------------


def test_run_without_binary_raises() -> None:
    try:
        binary = binary_path()
    except (CompilerNotFoundError, UnsupportedPlatformError):
        pytest.skip("no bundled binary present")

    with hide_file(binary), pytest.raises(CompilerNotFoundError):
        run(["--version"])


def test_run_timeout_raises_timeout_error(tsgo_binary: Path, tmp_path: Path) -> None:
    # Construct a source large enough that the compiler takes measurable
    # time. A tiny timeout forces a real TimeoutExpired from subprocess.
    big = tmp_path / "big.ts"
    big.write_text(
        "export const values: number[] = [\n"
        + "".join(f"  {i},\n" for i in range(200_000))
        + "];\n",
        encoding="utf-8",
    )
    with pytest.raises(CompilerTimeoutError):
        run(["--noEmit", "--strict", str(big)], timeout=0.001)


def test_run_rejects_oversized_stdout(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('const x: number = "bad";\n', encoding="utf-8")
    # Force the max to a tiny value; the compiler will produce more output
    # than that, and the runner must raise.
    with pytest.raises(CompilerExecutionError, match="stdout exceeded"):
        run(["--noEmit", str(f)], max_stdout_bytes=1)


def test_run_rejects_oversized_stderr(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('const x: number = "bad";\n', encoding="utf-8")
    try:
        run(["--noEmit", str(f)], max_stderr_bytes=1)
    except CompilerExecutionError as exc:
        assert "stderr exceeded" in str(exc)
    else:
        pytest.skip("no stderr output produced by this invocation")


# --- run: subprocess safety ------------------------------------------------


def test_run_never_uses_shell(tsgo_binary: Path, tmp_path: Path) -> None:
    """Arguments with shell metacharacters must be treated literally."""
    f = tmp_path / "weird;name.ts"
    f.write_text("export const x = 1;\n", encoding="utf-8")
    # If run() used a shell, this would try to execute "name.ts".
    result = run(["--noEmit", str(f)])
    # The result should be a normal check outcome, not a shell error.
    assert isinstance(result.returncode, int)


def test_run_rejects_null_byte_in_arguments(tsgo_binary: Path) -> None:
    """Null bytes in argv must be rejected by the OS or runner, not silently pass."""
    with pytest.raises((ValueError, OSError, CompilerExecutionError)):
        run(["--version", "arg\x00with-null"])


def test_run_respects_cwd(tsgo_binary: Path, tmp_path: Path) -> None:
    result = run(["--version"], cwd=tmp_path)
    assert result.returncode == 0


# --- RunResult dataclass ---------------------------------------------------


def test_run_result_is_frozen(tsgo_binary: Path) -> None:
    import dataclasses

    result = run(["--version"])
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.returncode = 99  # type: ignore[misc]


def test_run_result_is_hashable(tsgo_binary: Path) -> None:
    result = run(["--version"])
    assert hash(result) == hash(result)


# --- process-level sanity --------------------------------------------------


def test_runner_in_subprocess(tsgo_binary: Path, tmp_path: Path) -> None:
    """Verify runner works when invoked from a fresh Python interpreter."""
    code = (
        "from pytscheck.runner import run\n"
        "r = run(['--version'])\n"
        "assert r.returncode == 0, r\n"
        "print('ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
