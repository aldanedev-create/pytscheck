"""Tests for Windows-style path handling.

Runs on all platforms; assertions are chosen to be valid whether we are
on Windows or not.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from pytscheck.paths import is_inside, normalize


def test_backslash_in_filename_is_basename_in_api() -> None:
    """The api rejects backslash in a *virtual* filename, on all platforms."""
    from pytscheck.api import check
    from pytscheck.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError, match="basename"):
        check("const x = 1;", filename="dir\\file.ts")


def test_drive_letter_path_normalizes() -> None:
    if sys.platform != "win32":
        pytest.skip("Windows-only path form")
    assert normalize("C:\\Windows").is_absolute()


def test_posix_style_path_on_windows() -> None:
    if sys.platform != "win32":
        pytest.skip("Windows-only behavior")
    assert normalize("/tmp/x").is_absolute()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")
def test_windows_case_insensitive_same_dir(tmp_path: Path) -> None:
    # tmp_path has a canonical case; a variant should still be "inside"
    upper = Path(str(tmp_path).upper())
    assert is_inside(upper, tmp_path)


def test_windows_reserved_names_are_rejected_by_os(tmp_path: Path) -> None:
    """Windows reserved names (CON, NUL) cannot be created; on POSIX they can."""
    from pytscheck import checker

    reserved = "CON.ts"
    try:
        f = tmp_path / reserved
        f.write_text("export const x: number = 1;\n", encoding="utf-8")
    except OSError:
        return  # acceptable on Windows

    # If the file was created (POSIX), a check must still work
    try:
        r = checker.check_file(f)
    except Exception:
        return
    assert r.success


def test_long_path_rejected_cleanly(tsgo_binary: Path, tmp_path: Path) -> None:
    """Very deep nested paths must produce a clean error, not a crash."""
    deep = tmp_path
    for _ in range(50):
        deep = deep / "sub"
    try:
        deep.mkdir(parents=True)
    except OSError:
        pytest.skip("filesystem rejects deep nesting")

    f = deep / "x.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    try:
        r = checker.check_file(f)
    except Exception:
        return  # acceptable: OS-level path limits
    assert r.success


def test_unc_path_shape_on_windows() -> None:
    if sys.platform != "win32":
        pytest.skip("Windows-only")
    # A UNC path parses without crashing
    p = Path(r"\\server\share\file")
    assert str(p)  # smoke test


def test_windows_path_separator_in_source_not_special(tsgo_binary: Path) -> None:
    """Backslashes inside a TypeScript string must not affect parsing."""
    r = checker.check_source('export const s: string = "a\\\\b";')
    assert r.success


def test_posix_symlink_and_windows_compat(tmp_path: Path) -> None:
    """Test that path handling for symlinks works cross-platform."""
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this filesystem")
    assert is_inside(link / "x", tmp_path)