"""Tests for behavior when the bundled binary is missing.

Uses real filesystem operations to temporarily remove the binary. Never
stubs the runner or subprocess.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck.exceptions import CompilerExecutionError, CompilerNotFoundError
from pytscheck.runner import binary_path, run
from tests.helpers import hide_file


@pytest.fixture
def hidden_binary():
    """Temporarily hide the real bundled binary, restoring it afterward."""
    try:
        binary = binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")
    with hide_file(binary):
        yield binary


def test_binary_path_raises_when_missing(hidden_binary: Path) -> None:
    with pytest.raises(CompilerNotFoundError, match="not found"):
        binary_path()


def test_run_raises_when_missing(hidden_binary: Path) -> None:
    with pytest.raises(CompilerNotFoundError):
        run(["--version"])


def test_check_source_raises_when_missing(hidden_binary: Path) -> None:
    from pytscheck import checker

    with pytest.raises((CompilerNotFoundError, CompilerExecutionError)):
        checker.check_source("const x = 1;")


def test_check_file_raises_when_missing(hidden_binary: Path, tmp_path: Path) -> None:
    from pytscheck import checker

    f = tmp_path / "a.ts"
    f.write_text("const x = 1;\n", encoding="utf-8")
    with pytest.raises((CompilerNotFoundError, CompilerExecutionError)):
        checker.check_file(f)


def test_check_project_raises_when_missing(hidden_binary: Path, tmp_path: Path) -> None:
    from pytscheck import checker

    (tmp_path / "tsconfig.json").write_text('{"compilerOptions":{}}')
    with pytest.raises((CompilerNotFoundError, CompilerExecutionError)):
        checker.check_project(tmp_path)


def test_public_api_raises_when_missing(hidden_binary: Path) -> None:
    from pytscheck import check

    with pytest.raises((CompilerNotFoundError, CompilerExecutionError)):
        check("const x = 1;")


def test_cli_reports_operational_error_when_missing(hidden_binary: Path) -> None:
    from pytscheck.__main__ import EXIT_OPERATIONAL
    from tests.helpers import run_cli

    code, _, err = run_cli(["string", "const x = 1;"])
    assert code == EXIT_OPERATIONAL
    assert "Traceback" not in err


def test_binary_restored_after_fixture() -> None:
    """After the fixture exits, binary_path must succeed again."""
    try:
        original = binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    with hide_file(original), pytest.raises(CompilerNotFoundError):
        binary_path()

    assert binary_path() == original


def test_error_message_mentions_build_script(hidden_binary: Path) -> None:
    with pytest.raises(CompilerNotFoundError, match="build_binaries"):
        binary_path()
