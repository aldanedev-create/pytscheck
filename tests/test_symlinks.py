"""Tests for symlink handling."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from pytscheck import checker
from pytscheck.paths import is_inside

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" and os.environ.get("CI") == "true",
    reason="Windows CI runners may not permit symlink creation",
)


def _try_symlink(target: Path, link: Path, *, is_dir: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=is_dir)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks not supported: {exc}")


def test_check_file_through_symlink(tsgo_binary: Path, tmp_path: Path) -> None:
    real = tmp_path / "real.ts"
    real.write_text("export const x: number = 1;\n", encoding="utf-8")
    link = tmp_path / "link.ts"
    _try_symlink(real, link)
    r = checker.check_file(link)
    assert r.success


def test_check_file_through_broken_symlink(tmp_path: Path) -> None:
    link = tmp_path / "broken.ts"
    _try_symlink(tmp_path / "nonexistent.ts", link)
    from pytscheck.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError):
        checker.check_file(link)


def test_is_inside_resolves_symlinks(tmp_path: Path) -> None:
    target = tmp_path / "real"
    target.mkdir()
    link = tmp_path / "link"
    _try_symlink(target, link, is_dir=True)
    assert is_inside(link / "x", tmp_path)


def test_is_inside_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "escape"
    _try_symlink(outside, link, is_dir=True)
    # link/x resolves to outside/x, which is not inside tmp_path
    assert not is_inside(link / "x", tmp_path)


def test_check_project_with_symlinked_file(tsgo_binary: Path, tmp_path: Path) -> None:
    real = tmp_path / "real.ts"
    real.write_text("export const x: number = 1;\n", encoding="utf-8")
    link = tmp_path / "link.ts"
    _try_symlink(real, link)
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, "include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    r = checker.check_project(tmp_path)
    assert r.success


def test_check_project_with_symlinked_directory(tsgo_binary: Path, tmp_path: Path) -> None:
    realdir = tmp_path / "realdir"
    realdir.mkdir()
    (realdir / "a.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    link = tmp_path / "linkdir"
    _try_symlink(realdir, link, is_dir=True)
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, "include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    # Depending on tsgo's resolution, it may or may not follow the link.
    r = checker.check_project(tmp_path)
    assert r.success


def test_symlink_loop_is_handled(tmp_path: Path) -> None:
    """A symlink pointing at itself must not cause infinite recursion."""
    link = tmp_path / "loop.ts"
    _try_symlink(link, link)
    from pytscheck.exceptions import ConfigurationError

    with pytest.raises((ConfigurationError, OSError)):
        checker.check_file(link)


def test_relative_symlink_resolution(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    try:
        os.symlink("real", link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("relative symlinks not supported")
    assert is_inside(link / "x", tmp_path)
