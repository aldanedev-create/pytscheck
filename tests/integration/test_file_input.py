"""Integration tests for checking individual files."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import check_file
from tests.assertions import assert_has_error_code, assert_valid_result


def test_valid_file(tsgo_binary, ts_file_valid: Path) -> None:
    r = check_file(ts_file_valid)
    assert_valid_result(r)
    assert r.success


def test_file_with_type_error(tsgo_binary, ts_file_type_error: Path) -> None:
    r = check_file(ts_file_type_error)
    assert not r.success
    assert_has_error_code(r, 2322)


def test_file_with_syntax_error(tsgo_binary, ts_file_syntax_error: Path) -> None:
    r = check_file(ts_file_syntax_error)
    assert not r.success


def test_file_accepts_string_path(tsgo_binary, ts_file_valid: Path) -> None:
    r = check_file(str(ts_file_valid))
    assert r.success


def test_file_accepts_pathlib_path(tsgo_binary, ts_file_valid: Path) -> None:
    r = check_file(ts_file_valid)
    assert r.success


def test_missing_file_raises(tmp_path: Path) -> None:
    from pytscheck.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError, match="does not exist"):
        check_file(tmp_path / "missing.ts")


def test_directory_raises(tmp_path: Path) -> None:
    from pytscheck.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError, match="not a file"):
        check_file(tmp_path)


def test_diagnostic_file_matches_input(tsgo_binary, ts_file_type_error: Path) -> None:
    r = check_file(ts_file_type_error)
    for d in r.errors:
        assert d.file is not None
        assert ts_file_type_error.name in d.file


def test_file_with_unicode_content(tsgo_binary, tmp_path: Path) -> None:
    f = tmp_path / "u.ts"
    f.write_text('export const s: string = "héllo 世界";\n', encoding="utf-8")
    r = check_file(f)
    assert r.success


def test_file_with_unicode_name(tsgo_binary, tmp_path: Path) -> None:
    f = tmp_path / "café.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    r = check_file(f)
    assert r.success


def test_file_with_spaces_in_name(tsgo_binary, tmp_path: Path) -> None:
    f = tmp_path / "my file.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    r = check_file(f)
    assert r.success


def test_file_with_crlf_line_endings(tsgo_binary, tmp_path: Path) -> None:
    f = tmp_path / "crlf.ts"
    f.write_bytes(b"export const x: number = 1;\r\n")
    r = check_file(f)
    assert r.success


def test_file_with_utf8_bom(tsgo_binary, tmp_path: Path) -> None:
    f = tmp_path / "bom.ts"
    f.write_bytes("\ufeffexport const x: number = 1;\n".encode("utf-8"))
    r = check_file(f)
    assert_valid_result(r)


def test_empty_file(tsgo_binary, tmp_path: Path) -> None:
    f = tmp_path / "empty.ts"
    f.write_text("", encoding="utf-8")
    r = check_file(f)
    assert r.success


def test_multiple_files_independent(tsgo_binary, tmp_path: Path) -> None:
    good = tmp_path / "good.ts"
    good.write_text("export const x: number = 1;\n", encoding="utf-8")
    bad = tmp_path / "bad.ts"
    bad.write_text('export const x: number = "s";\n', encoding="utf-8")

    assert check_file(good).success
    assert not check_file(bad).success
    assert check_file(good).success


def test_file_check_does_not_emit_output(tsgo_binary, tmp_path: Path) -> None:
    """No .js should be produced next to a checked .ts file."""
    f = tmp_path / "input.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    check_file(f)
    assert not (tmp_path / "input.js").exists()
    assert not (tmp_path / "input.d.ts").exists()
    assert not (tmp_path / "input.js.map").exists()
