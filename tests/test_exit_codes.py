"""Tests for CLI exit codes and their stability."""

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
from tests.helpers import run_cli, run_cli_subprocess


def test_exit_codes_are_distinct() -> None:
    codes = {EXIT_OK, EXIT_TYPE_ERRORS, EXIT_USAGE, EXIT_OPERATIONAL}
    assert len(codes) == 4


def test_exit_codes_are_small_nonneg_ints() -> None:
    for code in (EXIT_OK, EXIT_TYPE_ERRORS, EXIT_USAGE, EXIT_OPERATIONAL):
        assert isinstance(code, int)
        assert 0 <= code < 128


def test_success_exit_code_is_zero(tsgo_binary: Path) -> None:
    code, _, _ = run_cli(["string", "export const x: number = 1;"])
    assert code == EXIT_OK


def test_type_error_exit_code_is_one(tsgo_binary: Path) -> None:
    code, _, _ = run_cli(["string", 'const age: number = "twenty";'])
    assert code == EXIT_TYPE_ERRORS


def test_usage_error_exit_code_is_two() -> None:
    code, _, _ = run_cli([])
    assert code == EXIT_USAGE


def test_operational_error_exit_code_is_three() -> None:
    from pytscheck.runner import binary_path
    from tests.helpers import hide_file

    try:
        original = binary_path()
    except Exception:
        code, _, _ = run_cli(["string", "const x = 1;"])
        assert code == EXIT_OPERATIONAL
        return

    with hide_file(original):
        code, _, _ = run_cli(["string", "const x = 1;"])
        assert code == EXIT_OPERATIONAL


def test_missing_file_yields_usage_or_operational(tmp_path: Path) -> None:
    code, _, _ = run_cli(["file", str(tmp_path / "missing.ts")])
    assert code in {EXIT_USAGE, EXIT_OPERATIONAL}


def test_missing_project_yields_usage_or_operational(tmp_path: Path) -> None:
    code, _, _ = run_cli(["project", str(tmp_path / "missing")])
    assert code in {EXIT_USAGE, EXIT_OPERATIONAL}


def test_subprocess_exit_code_matches_in_process(tsgo_binary: Path) -> None:
    in_process = run_cli(["string", "export const x: number = 1;"])[0]
    sub = run_cli_subprocess(["string", "export const x: number = 1;"])
    assert sub.returncode == in_process


def test_unknown_subcommand_raises_system_exit() -> None:
    with pytest.raises(SystemExit):
        run_cli(["nonsense"])


def test_unknown_subcommand_exit_code() -> None:
    sub = run_cli_subprocess(["nonsense"])
    # argparse's default for unknown subcommand is 2
    assert sub.returncode != 0


def test_version_flag_exits_zero() -> None:
    sub = run_cli_subprocess(["--version"])
    assert sub.returncode == EXIT_OK


def test_no_args_exits_usage() -> None:
    sub = run_cli_subprocess([])
    assert sub.returncode == EXIT_USAGE