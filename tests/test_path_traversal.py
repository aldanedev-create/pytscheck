"""Tests that path traversal attempts are rejected."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck.exceptions import ConfigurationError
from pytscheck.paths import assert_inside, is_inside
from pytscheck.resolver import resolve_project


def test_assert_inside_rejects_dotdot(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="escapes"):
        assert_inside(tmp_path / ".." / "sibling", tmp_path)


def test_assert_inside_rejects_absolute_outside(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError):
        assert_inside(Path("/etc"), tmp_path)


def test_is_inside_rejects_dotdot_after_resolution(tmp_path: Path) -> None:
    assert not is_inside(tmp_path / ".." / "x", tmp_path)


def test_resolve_project_rejects_extends_escape(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        '{"extends": "../../etc/passwd"}', encoding="utf-8"
    )
    with pytest.raises(ConfigurationError, match="escapes"):
        resolve_project(tmp_path)


def test_resolve_project_rejects_absolute_extends_escape(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        '{"extends": "/etc/passwd"}', encoding="utf-8"
    )
    with pytest.raises(ConfigurationError):
        resolve_project(tmp_path)


def test_resolve_project_accepts_extends_inside(tmp_path: Path) -> None:
    (tmp_path / "base.json").write_text("{}")
    (tmp_path / "tsconfig.json").write_text('{"extends": "./base.json"}')
    rp = resolve_project(tmp_path)
    assert rp.extends == "./base.json"


def test_resolve_project_accepts_nested_extends_inside(tmp_path: Path) -> None:
    sub = tmp_path / "configs"
    sub.mkdir()
    (sub / "base.json").write_text("{}")
    (tmp_path / "tsconfig.json").write_text('{"extends": "./configs/base.json"}')
    rp = resolve_project(tmp_path)
    assert rp.extends == "./configs/base.json"


def test_check_api_rejects_filename_with_slash() -> None:
    from pytscheck.api import check

    with pytest.raises(ConfigurationError, match="basename"):
        check("const x = 1;", filename="../escape.ts")


def test_check_api_rejects_filename_with_backslash() -> None:
    from pytscheck.api import check

    with pytest.raises(ConfigurationError, match="basename"):
        check("const x = 1;", filename="..\\escape.ts")


def test_check_api_rejects_nul_in_filename() -> None:
    from pytscheck.api import check

    with pytest.raises(ConfigurationError, match="NUL"):
        check("const x = 1;", filename="a\x00b.ts")


def test_check_file_does_not_follow_escape_via_path(tmp_path: Path) -> None:
    """A missing file that resolves outside the cwd still raises ConfigurationError."""
    from pytscheck import checker

    with pytest.raises(ConfigurationError):
        checker.check_file(tmp_path / ".." / "nonexistent.ts")


def test_check_project_does_not_follow_escape_via_path(tmp_path: Path) -> None:
    from pytscheck import checker

    with pytest.raises(ConfigurationError):
        checker.check_project(tmp_path / ".." / "nonexistent")


def test_relative_symlink_cannot_escape(tmp_path: Path) -> None:
    import os
    import sys

    if sys.platform == "win32":
        pytest.skip("POSIX-only symlink test")
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "escape"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")
    assert not is_inside(link / "x", tmp_path)