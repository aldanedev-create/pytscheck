"""Tests for pytscheck.paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck.exceptions import ConfigurationError
from pytscheck.paths import (
    assert_inside,
    assert_no_null_bytes,
    is_inside,
    normalize,
)


# --- normalize --------------------------------------------------------------


def test_normalize_absolute(tmp_path: Path) -> None:
    assert normalize(tmp_path) == tmp_path.resolve()


def test_normalize_expands_user(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert normalize("~") == tmp_path.resolve()


def test_normalize_relative(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert normalize("foo/bar") == (tmp_path / "foo" / "bar").resolve()


def test_normalize_collapses_dots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert normalize("a/./b/../c") == (tmp_path / "a" / "c").resolve()


def test_normalize_accepts_path_object(tmp_path: Path) -> None:
    assert normalize(tmp_path) == tmp_path.resolve()


def test_normalize_returns_absolute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert normalize("x").is_absolute()


# --- is_inside --------------------------------------------------------------


def test_is_inside_true(tmp_path: Path) -> None:
    assert is_inside(tmp_path / "a" / "b", tmp_path)


def test_is_inside_self(tmp_path: Path) -> None:
    assert is_inside(tmp_path, tmp_path)


def test_is_inside_false(tmp_path: Path) -> None:
    assert not is_inside(tmp_path.parent / "somewhere-else", tmp_path)


def test_is_inside_defeats_traversal(tmp_path: Path) -> None:
    assert not is_inside(tmp_path / ".." / "outside", tmp_path)


def test_is_inside_resolves_symlinks(tmp_path: Path) -> None:
    (tmp_path / "real").mkdir()
    (tmp_path / "link").symlink_to(tmp_path / "real")
    # The symlink resolves into real, which is inside tmp_path
    assert is_inside(tmp_path / "link" / "x", tmp_path)


# --- assert_inside ----------------------------------------------------------


def test_assert_inside_ok(tmp_path: Path) -> None:
    assert_inside(tmp_path / "a", tmp_path)


def test_assert_inside_raises(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="escapes its root"):
        assert_inside(tmp_path.parent / "outside", tmp_path)


def test_assert_inside_custom_description(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="module"):
        assert_inside(tmp_path.parent, tmp_path, what="module")


# --- assert_no_null_bytes ---------------------------------------------------


def test_assert_no_null_bytes_ok() -> None:
    assert_no_null_bytes("hello")
    assert_no_null_bytes("")
    assert_no_null_bytes("emoji 🙂 ok")


def test_assert_no_null_bytes_raises() -> None:
    with pytest.raises(ConfigurationError, match="NUL"):
        assert_no_null_bytes("hel\x00lo")


def test_assert_no_null_bytes_custom_description() -> None:
    with pytest.raises(ConfigurationError, match="filename"):
        assert_no_null_bytes("\x00", what="filename")


# --- module exports --------------------------------------------------------


def test_paths_all_names_exist() -> None:
    from pytscheck import paths

    for name in paths.__all__:
        assert hasattr(paths, name), f"missing: {name}"