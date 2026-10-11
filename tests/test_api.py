"""Tests for pytscheck.api.

These exercise the real public API against real files and the real bundled
compiler. Tests that require the binary skip if it is not present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck.api import check, check_file, check_project
from pytscheck.config import CompilerOptions
from pytscheck.exceptions import ConfigurationError, PyTSCheckError
from tests.assertions import (
    assert_has_error_code,
    assert_no_diagnostics,
    assert_valid_result,
)


# --- validation (no binary needed) -----------------------------------------


def test_check_rejects_null_byte_in_source() -> None:
    with pytest.raises(ConfigurationError, match="NUL"):
        check("const x: number = 1;\x00")


def test_check_rejects_null_byte_in_filename() -> None:
    with pytest.raises(ConfigurationError, match="NUL"):
        check("const x = 1;", filename="a\x00b.ts")


@pytest.mark.parametrize("bad", ["dir/file.ts", "dir\\file.ts"])
def test_check_rejects_path_separators_in_filename(bad: str) -> None:
    with pytest.raises(ConfigurationError, match="basename"):
        check("const x = 1;", filename=bad)


def test_check_rejects_bad_options_type() -> None:
    with pytest.raises(ConfigurationError, match="options must be"):
        check("const x = 1;", options=42)  # type: ignore[arg-type]


def test_check_file_missing() -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        check_file("/nonexistent/path.ts")


def test_check_file_is_directory(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not a file"):
        check_file(tmp_path)


def test_check_project_missing() -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        check_project("/nonexistent/dir")


def test_check_project_not_directory(tmp_path: Path) -> None:
    f = tmp_path / "file"
    f.write_text("")
    with pytest.raises(ConfigurationError, match="not a directory"):
        check_project(f)


# --- real checks (require bundled binary) ----------------------------------


def test_check_valid_source(tsgo_binary: Path) -> None:
    r = check("export const answer: number = 42;")
    assert_valid_result(r)
    assert_no_diagnostics(r)


def test_check_type_error(tsgo_binary: Path) -> None:
    r = check('const age: number = "twenty";')
    assert_valid_result(r)
    assert not r.success
    assert_has_error_code(r, 2322)


def test_check_syntax_error(tsgo_binary: Path) -> None:
    r = check("const x: number = ;")
    assert_valid_result(r)
    assert not r.success
    assert r.errors


def test_check_custom_filename(tsgo_binary: Path) -> None:
    r = check('const age: number = "twenty";', filename="custom.ts")
    assert not r.success
    assert any(d.file == "custom.ts" for d in r.errors)


def test_check_keep_raw(tsgo_binary: Path) -> None:
    r = check('const age: number = "twenty";', keep_raw=True)
    assert r.raw_output is not None
    assert r.raw_output.strip()


def test_check_file_valid(tsgo_binary: Path, ts_file_valid: Path) -> None:
    r = check_file(ts_file_valid)
    assert_valid_result(r)
    assert r.success


def test_check_file_with_error(tsgo_binary: Path, ts_file_type_error: Path) -> None:
    r = check_file(ts_file_type_error)
    assert_valid_result(r)
    assert not r.success
    assert_has_error_code(r, 2322)


def test_check_file_accepts_string_path(tsgo_binary: Path, ts_file_valid: Path) -> None:
    r = check_file(str(ts_file_valid))
    assert r.success


def test_check_project_clean(tsgo_binary: Path, project_minimal: Path) -> None:
    r = check_project(project_minimal)
    assert_valid_result(r)
    assert r.success


def test_check_project_with_error(tsgo_binary: Path, project_type_error: Path) -> None:
    r = check_project(project_type_error)
    assert_valid_result(r)
    assert not r.success
    assert_has_error_code(r, 2322)


def test_check_with_options_dict(tsgo_binary: Path) -> None:
    r = check("export const x: number = 1;", options={"strict": True})
    assert_valid_result(r)
    assert r.success


def test_check_with_options_instance(tsgo_binary: Path) -> None:
    r = check("export const x: number = 1;", options=CompilerOptions(strict=True))
    assert_valid_result(r)
    assert r.success


def test_check_project_adapter_none_is_default(tsgo_binary: Path, project_minimal: Path) -> None:
    r = check_project(project_minimal, adapter=None)
    assert_valid_result(r)
    assert r.success


# --- error propagation -----------------------------------------------------


def test_check_without_binary_raises_operational() -> None:
    """When the binary is missing, check() must raise, not return success."""
    from tests.helpers import hide_file

    from pytscheck import runner

    try:
        binary = runner.binary_path()
    except PyTSCheckError:
        # Already missing; verify check() raises
        with pytest.raises(PyTSCheckError):
            check("const x = 1;")
        return

    with hide_file(binary):
        with pytest.raises(PyTSCheckError):
            check("const x = 1;")