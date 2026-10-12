"""Unit tests for path normalization and safety."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pytscheck.exceptions import ConfigurationError
from pytscheck.paths import (
    assert_inside,
    assert_no_null_bytes,
    is_inside,
    normalize,
)

# --- normalization ----------------------------------------------------------


def test_absolute_path_unchanged(tmp_path: Path) -> None:
    assert normalize(tmp_path) == tmp_path.resolve()


def test_relative_path_resolved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert normalize("a") == (tmp_path / "a").resolve()


def test_dot_and_dotdot_collapsed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert normalize("./a/../b") == (tmp_path / "b").resolve()


def test_tilde_expanded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert normalize("~") == tmp_path.resolve()


def test_tilde_subpath_expanded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert normalize("~/sub") == (tmp_path / "sub").resolve()


def test_str_input_accepted(tmp_path: Path) -> None:
    assert normalize(str(tmp_path)) == tmp_path.resolve()


def test_pathlib_input_accepted(tmp_path: Path) -> None:
    assert normalize(tmp_path) == tmp_path.resolve()


def test_result_is_absolute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert normalize("x").is_absolute()


def test_result_is_resolved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    p = normalize("x")
    assert p == p.resolve()


# --- containment ------------------------------------------------------------


def test_is_inside_self(tmp_path: Path) -> None:
    assert is_inside(tmp_path, tmp_path)


def test_is_inside_child(tmp_path: Path) -> None:
    assert is_inside(tmp_path / "a" / "b", tmp_path)


def test_is_inside_parent(tmp_path: Path) -> None:
    assert not is_inside(tmp_path.parent, tmp_path)


def test_is_inside_sibling(tmp_path: Path) -> None:
    assert not is_inside(tmp_path.parent / "sibling", tmp_path)


def test_is_inside_traversal_denied(tmp_path: Path) -> None:
    assert not is_inside(tmp_path / ".." / "escape", tmp_path)


def test_assert_inside_passes(tmp_path: Path) -> None:
    assert_inside(tmp_path / "x", tmp_path)


def test_assert_inside_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="escapes"):
        assert_inside(tmp_path / ".." / "escape", tmp_path)


def test_assert_inside_custom_what(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="target"):
        assert_inside(tmp_path.parent, tmp_path, what="target")


# --- null byte rejection ---------------------------------------------------


def test_rejects_nul() -> None:
    with pytest.raises(ConfigurationError, match="NUL"):
        assert_no_null_bytes("a\x00b")


def test_accepts_plain_string() -> None:
    assert_no_null_bytes("hello")


def test_accepts_empty_string() -> None:
    assert_no_null_bytes("")


def test_accepts_unicode() -> None:
    assert_no_null_bytes("héllo 世界 🌍")


def test_custom_what_in_error() -> None:
    with pytest.raises(ConfigurationError, match="filename"):
        assert_no_null_bytes("x\x00", what="filename")


# --- platform-specific ------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
def test_posix_symlink_resolution(tmp_path: Path) -> None:
    target = tmp_path / "real"
    target.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")
    assert is_inside(link / "x", tmp_path)


def test_case_sensitivity_documented() -> None:
    """On POSIX, path comparison is case-sensitive; on Windows it is not.
    This documents the behavior rather than asserting a specific outcome."""
    if sys.platform == "win32":
        # Windows paths are case-insensitive at the OS level
        assert Path("C:/Foo").resolve() == Path("c:/foo").resolve()
    else:
        assert Path("/tmp/Foo") != Path("/tmp/foo")
