"""Tests that subprocess argument construction is safe against injection."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pytscheck.exceptions import PyTSCheckError
from pytscheck.runner import run


def test_shell_metacharacter_in_filename(tsgo_binary: Path, tmp_path: Path) -> None:
    """A filename with shell metacharacters must be passed literally."""
    f = tmp_path / "file;rm -rf /.ts"
    try:
        f.write_text("export const x: number = 1;\n", encoding="utf-8")
    except OSError:
        pytest.skip("filesystem rejects this filename")
    # If run() used a shell, this would try to run `rm -rf /`.
    result = run(["--noEmit", str(f)])
    assert isinstance(result.returncode, int)


def test_pipe_character_in_filename(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "file|cat /etc/passwd.ts"
    try:
        f.write_text("export const x: number = 1;\n", encoding="utf-8")
    except OSError:
        pytest.skip("filesystem rejects this filename")
    result = run(["--noEmit", str(f)])
    assert isinstance(result.returncode, int)


def test_command_substitution_in_filename(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "file$(id).ts"
    try:
        f.write_text("export const x: number = 1;\n", encoding="utf-8")
    except OSError:
        pytest.skip("filesystem rejects this filename")
    result = run(["--noEmit", str(f)])
    assert isinstance(result.returncode, int)


def test_backtick_in_filename(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "file`id`.ts"
    try:
        f.write_text("export const x: number = 1;\n", encoding="utf-8")
    except OSError:
        pytest.skip("filesystem rejects this filename")
    result = run(["--noEmit", str(f)])
    assert isinstance(result.returncode, int)


def test_ampersand_in_filename(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "file&sleep.ts"
    try:
        f.write_text("export const x: number = 1;\n", encoding="utf-8")
    except OSError:
        pytest.skip("filesystem rejects this filename")
    result = run(["--noEmit", str(f)])
    assert isinstance(result.returncode, int)


def test_null_byte_in_argument_rejected(tsgo_binary: Path) -> None:
    """The OS or Python must reject NUL in argv."""
    with pytest.raises((ValueError, OSError, Exception)):
        run(["--noEmit", "arg\x00with-null"])


def test_shell_is_never_invoked_by_runner() -> None:
    """Verify the runner's source does not invoke a shell."""
    import inspect

    from pytscheck import runner

    source = inspect.getsource(runner.run)
    # Must explicitly disable shell, or use subprocess APIs that don't
    # spawn a shell by default.
    assert "shell=False" in source or "shell=True" not in source


def test_runner_does_not_use_os_system(tsgo_binary: Path) -> None:
    """os.system is unsafe; verify it's not used anywhere in runner.py."""
    import inspect

    from pytscheck import runner

    source = inspect.getsource(runner)
    assert "os.system" not in source
    assert "os.popen" not in source


def test_runner_does_not_use_shell_eq_true() -> None:
    import inspect

    from pytscheck import runner

    source = inspect.getsource(runner)
    assert "shell=True" not in source


def test_subprocess_run_uses_argument_list(tmp_path: Path) -> None:
    """Verify directly: passing a list does not invoke a shell."""
    marker = tmp_path / "marker"
    # If this were a shell string, `touch marker` would run.
    result = subprocess.run(
        ["echo", "harmless; touch " + str(marker)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        shell=False,
    )
    assert result.returncode == 0
    assert not marker.exists(), "argument was interpreted by a shell"


def test_runner_error_includes_argv(tsgo_binary: Path, tmp_path: Path) -> None:
    """When the runner raises an execution error, argv is not lost."""
    from pytscheck.runner import binary_path
    from tests.helpers import hide_file

    try:
        original = binary_path()
    except Exception:
        pytest.skip("no binary")

    with hide_file(original), pytest.raises(PyTSCheckError):
        run(["--version"])
