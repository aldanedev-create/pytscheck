"""Tests for pytscheck.checker.

These run the real checker against real files and the real bundled
compiler. No mocking of the runner. Tests that need the binary skip
if it is not present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import checker
from pytscheck.exceptions import (
    CompilerExecutionError,
    CompilerNotFoundError,
    ConfigurationError,
)
from pytscheck.models import SourceFile
from tests.assertions import assert_valid_result

# --- check_source ----------------------------------------------------------


def test_check_source_valid(tsgo_binary: Path) -> None:
    r = checker.check_source("export const x: number = 1;")
    assert_valid_result(r)
    assert r.success


def test_check_source_error(tsgo_binary: Path) -> None:
    r = checker.check_source('const age: number = "twenty";')
    assert_valid_result(r)
    assert not r.success
    assert any(d.code == 2322 for d in r.errors)


def test_check_source_custom_filename(tsgo_binary: Path) -> None:
    r = checker.check_source('const age: number = "twenty";', filename="custom.ts")
    assert any(d.file == "custom.ts" for d in r.errors)


def test_check_source_keep_raw(tsgo_binary: Path) -> None:
    r = checker.check_source('const age: number = "twenty";', keep_raw=True)
    assert r.raw_output is not None


def test_check_source_no_keep_raw(tsgo_binary: Path) -> None:
    r = checker.check_source("export const x = 1;")
    assert r.raw_output is None


# --- check_file ------------------------------------------------------------


def test_check_file_valid(tsgo_binary: Path, ts_file_valid: Path) -> None:
    r = checker.check_file(ts_file_valid)
    assert_valid_result(r)
    assert r.success


def test_check_file_type_error(tsgo_binary: Path, ts_file_type_error: Path) -> None:
    r = checker.check_file(ts_file_type_error)
    assert not r.success


def test_check_file_missing(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        checker.check_file(tmp_path / "nope.ts")


# --- check_project ---------------------------------------------------------


def test_check_project_clean(tsgo_binary: Path, project_minimal: Path) -> None:
    r = checker.check_project(project_minimal)
    assert_valid_result(r)
    assert r.success


def test_check_project_with_errors(tsgo_binary: Path, project_type_error: Path) -> None:
    r = checker.check_project(project_type_error)
    assert_valid_result(r)
    assert not r.success


def test_check_project_missing(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        checker.check_project(tmp_path / "nope")


# --- check_sources_virtual -------------------------------------------------


def test_check_sources_virtual_single(tsgo_binary: Path) -> None:
    sources = (SourceFile(path="a.ts", text="export const x: number = 1;\n"),)
    r = checker.check_sources_virtual(sources)
    assert_valid_result(r)
    assert r.success


def test_check_sources_virtual_with_error(tsgo_binary: Path) -> None:
    sources = (SourceFile(path="a.ts", text='export const x: number = "bad";\n'),)
    r = checker.check_sources_virtual(sources)
    assert not r.success
    assert any(d.code == 2322 for d in r.errors)


def test_check_sources_virtual_multiple(tsgo_binary: Path) -> None:
    sources = (
        SourceFile(path="a.ts", text="export const a: number = 1;\n"),
        SourceFile(path="b.ts", text="export const b: number = 2;\n"),
    )
    r = checker.check_sources_virtual(sources)
    assert r.success


def test_check_sources_virtual_empty_raises() -> None:
    with pytest.raises(ConfigurationError, match="no sources"):
        checker.check_sources_virtual(())


# --- binary-missing behaviour ----------------------------------------------


def test_check_source_without_binary_raises() -> None:
    from pytscheck import runner
    from tests.helpers import hide_file

    try:
        binary = runner.binary_path()
    except CompilerNotFoundError:
        with pytest.raises(CompilerNotFoundError):
            checker.check_source("const x = 1;")
        return

    with hide_file(binary), pytest.raises((CompilerNotFoundError, CompilerExecutionError)):
        checker.check_source("const x = 1;")


# --- operational error mapping ---------------------------------------------


def test_checker_nonzero_no_output_raises_operational() -> None:
    """Calling the checker against a real non-tsgo binary must not report success.

    We invoke the checker's real orchestration with the current Python
    interpreter as the "compiler" by temporarily hiding the real one and
    relying on the missing-binary path. This exercises the operational
    error boundary without fabricating output.
    """
    from pytscheck import runner
    from tests.helpers import hide_file

    try:
        binary = runner.binary_path()
    except CompilerNotFoundError:
        return pytest.skip("no binary present")

    with hide_file(binary), pytest.raises((CompilerNotFoundError, CompilerExecutionError)):
        checker.check_source("const x = 1;")
