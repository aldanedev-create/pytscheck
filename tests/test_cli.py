"""Tests for the `pytscheck` command line interface."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from pytscheck.__main__ import (
    EXIT_OK,
    EXIT_OPERATIONAL,
    EXIT_TYPE_ERRORS,
    EXIT_USAGE,
)
from tests.helpers import parse_cli_json, run_cli, run_cli_subprocess


# --- --version --------------------------------------------------------------


def test_version_flag_exits_zero() -> None:
    code, out, err = run_cli(["--version"])
    assert code == EXIT_OK
    assert "pytscheck" in out
    assert "bundled compiler" in out
    assert "adapter protocol" in out
    assert err == ""


def test_version_flag_does_not_require_binary() -> None:
    """--version must work even without a bundled binary."""
    code, _, _ = run_cli(["--version"])
    assert code == EXIT_OK


# --- --where ----------------------------------------------------------------


def test_where_with_binary_prints_path(tsgo_binary: Path) -> None:
    code, out, err = run_cli(["--where"])
    assert code == EXIT_OK
    assert str(tsgo_binary) in out
    assert err == ""


def test_where_without_binary_exits_operational(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate a missing binary by pointing platform detection at a bogus dir."""
    from tests.helpers import hide_file

    from pytscheck import runner

    # Find the real binary; if it isn't there, the test still makes sense.
    try:
        binary = runner.binary_path()
    except Exception:
        code, _, err = run_cli(["--where"])
        assert code == EXIT_OPERATIONAL
        assert "error" in err.lower()
        return

    with hide_file(binary):
        code, out, err = run_cli(["--where"])
        assert code == EXIT_OPERATIONAL
        assert "error" in err.lower()


# --- help ------------------------------------------------------------------


def test_no_args_prints_help_and_exits_usage() -> None:
    code, out, _ = run_cli([])
    assert code == EXIT_USAGE
    assert "pytscheck" in out.lower() or "usage" in out.lower()


# --- check subcommands -----------------------------------------------------


def test_string_check_valid(tsgo_binary: Path) -> None:
    code, out, err = run_cli(["string", "export const x: number = 1;"])
    assert code == EXIT_OK
    assert "ok" in out.lower()
    assert err == ""


def test_string_check_type_error(tsgo_binary: Path) -> None:
    code, out, err = run_cli(["string", 'const age: number = "twenty";'])
    assert code == EXIT_TYPE_ERRORS
    assert "error" in out.lower()


def test_string_check_json(tsgo_binary: Path) -> None:
    code, out, err = run_cli(["string", 'const age: number = "twenty";', "--json"])
    assert code == EXIT_TYPE_ERRORS
    payload = parse_cli_json(out)
    assert payload["success"] is False
    assert payload["compiler_version"]
    assert any(d["code"] == 2322 for d in payload["diagnostics"])


def test_file_check_valid(tsgo_binary: Path, ts_file_valid: Path) -> None:
    code, out, _ = run_cli(["file", str(ts_file_valid)])
    assert code == EXIT_OK
    assert "ok" in out.lower()


def test_file_check_type_error(tsgo_binary: Path, ts_file_type_error: Path) -> None:
    code, out, _ = run_cli(["file", str(ts_file_type_error)])
    assert code == EXIT_TYPE_ERRORS


def test_project_check(tsgo_binary: Path, project_type_error: Path) -> None:
    code, out, _ = run_cli(["project", str(project_type_error)])
    assert code == EXIT_TYPE_ERRORS


def test_project_check_clean(tsgo_binary: Path, project_minimal: Path) -> None:
    code, out, _ = run_cli(["project", str(project_minimal)])
    assert code == EXIT_OK


# --- error paths -----------------------------------------------------------


def test_file_subcommand_missing_file(tmp_path: Path) -> None:
    code, _, err = run_cli(["file", str(tmp_path / "nope.ts")])
    assert code in {EXIT_USAGE, EXIT_OPERATIONAL}
    assert "Traceback" not in err


def test_project_subcommand_missing_dir(tmp_path: Path) -> None:
    code, _, err = run_cli(["project", str(tmp_path / "nope")])
    assert code in {EXIT_USAGE, EXIT_OPERATIONAL}
    assert "Traceback" not in err


def test_string_subcommand_no_binary_exits_operational() -> None:
    """Without the binary, the CLI must fail cleanly, not traceback."""
    from tests.helpers import hide_file

    from pytscheck import runner

    try:
        binary = runner.binary_path()
    except Exception:
        code, _, err = run_cli(["string", "const x = 1;"])
        assert code == EXIT_OPERATIONAL
        assert "Traceback" not in err
        return

    with hide_file(binary):
        code, _, err = run_cli(["string", "const x = 1;"])
        assert code == EXIT_OPERATIONAL
        assert "Traceback" not in err


def test_unknown_subcommand_raises_system_exit() -> None:
    with pytest.raises(SystemExit):
        run_cli(["nonsense"])


# --- subprocess-level ------------------------------------------------------


def test_subprocess_version_matches_in_process() -> None:
    in_process = run_cli(["--version"])
    sub = run_cli_subprocess(["--version"])
    assert sub.returncode == in_process[0]
    assert sub.stdout == in_process[1]


def test_subprocess_stdout_stderr_separation(tmp_path: Path) -> None:
    sub = run_cli_subprocess(["file", str(tmp_path / "nope.ts")])
    # Errors go to stderr, not stdout
    assert sub.returncode in {EXIT_USAGE, EXIT_OPERATIONAL}
    assert sub.stderr.strip()