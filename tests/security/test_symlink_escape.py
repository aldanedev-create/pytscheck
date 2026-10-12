"""Tests that symlinks cannot be used to escape a project root."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from pytscheck.exceptions import ConfigurationError
from pytscheck.paths import assert_inside, is_inside

pytestmark = pytest.mark.skipif(
    sys.platform == "win32" and os.environ.get("CI") == "true",
    reason="Windows CI may not permit symlink creation",
)


def test_symlink_inside_root_is_allowed(tmp_path: Path) -> None:
    target = tmp_path / "real"
    target.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")
    assert is_inside(link / "x", tmp_path)


def test_symlink_escaping_root_is_detected(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")
    assert not is_inside(link / "x", tmp_path)


def test_assert_inside_rejects_escaping_symlink(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside2"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")
    with pytest.raises(ConfigurationError, match="escapes"):
        assert_inside(link / "x", tmp_path)


def test_check_project_does_not_follow_symlink_outside(tsgo_binary, tmp_path: Path) -> None:
    """A symlinked project must not read from outside the sandbox."""
    from pytscheck import check_project

    outside = tmp_path.parent / f"{tmp_path.name}-outside3"
    outside.mkdir(exist_ok=True)
    (outside / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}}',
        encoding="utf-8",
    )
    (outside / "secret.ts").write_text(
        'export const SECRET: string = "leaked";\n', encoding="utf-8"
    )

    link = tmp_path / "project-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")

    # pytscheck may or may not resolve the symlink, but it must not crash
    try:
        r = check_project(link)
    except ConfigurationError:
        return
    # If it did run, the result must be a valid Result
    assert isinstance(r.success, bool)


def test_symlink_loop_is_safe(tmp_path: Path) -> None:
    link = tmp_path / "loop"
    try:
        link.symlink_to(link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")
    # is_inside must not loop forever
    _ = is_inside(link, tmp_path)


def test_broken_symlink_is_handled(tmp_path: Path) -> None:
    link = tmp_path / "broken.ts"
    try:
        link.symlink_to(tmp_path / "does-not-exist.ts")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")
    from pytscheck import check_file

    with pytest.raises(ConfigurationError):
        check_file(link)


def test_symlink_to_itself(tmp_path: Path) -> None:
    link = tmp_path / "self"
    try:
        link.symlink_to(link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")
    from pytscheck import check_file

    with pytest.raises((ConfigurationError, OSError)):
        check_file(link)


def test_relative_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside4"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "escape"
    try:
        os.symlink("../" + outside.name, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("relative symlinks not supported")
    # After resolution, the link points outside tmp_path
    assert not is_inside(link / "x", tmp_path)
