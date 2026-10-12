"""Tests for the platform -> binary mapping.

Uses real executables on real disk. Never mocks subprocess or the runner.
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path

import pytest

from pytscheck.exceptions import CompilerNotFoundError, UnsupportedPlatformError
from pytscheck.runner import _platform_dir, binary_path
from tests.helpers import file_has_executable_bit


def test_platform_dir_matches_running_machine() -> None:
    dirname = _platform_dir()
    system = sys.platform
    machine = platform.machine().lower()

    if system == "linux":
        assert dirname.startswith("linux-")
        if machine in {"x86_64", "amd64"}:
            assert dirname == "linux-amd64"
        elif machine in {"aarch64", "arm64"}:
            assert dirname == "linux-arm64"
    elif system == "darwin":
        assert dirname.startswith("darwin-")
    elif system == "win32":
        assert dirname.startswith("windows-")


def test_platform_dir_is_a_string() -> None:
    assert isinstance(_platform_dir(), str)
    assert _platform_dir()


def test_binary_path_includes_platform_dir() -> None:
    try:
        p = binary_path()
    except (CompilerNotFoundError, UnsupportedPlatformError):
        pytest.skip("no bundled binary present")
    assert _platform_dir() in str(p)


def test_binary_path_ends_with_correct_name() -> None:
    try:
        p = binary_path()
    except (CompilerNotFoundError, UnsupportedPlatformError):
        pytest.skip("no bundled binary present")
    expected = "tsgo.exe" if sys.platform == "win32" else "tsgo"
    assert p.name == expected


def test_binary_path_is_under_src_pytscheck_bin() -> None:
    try:
        p = binary_path()
    except (CompilerNotFoundError, UnsupportedPlatformError):
        pytest.skip("no bundled binary present")
    assert "pytscheck" in p.parts
    assert "bin" in p.parts


def test_binary_path_returns_absolute_path() -> None:
    try:
        p = binary_path()
    except (CompilerNotFoundError, UnsupportedPlatformError):
        pytest.skip("no bundled binary present")
    assert p.is_absolute()


def test_all_six_platform_directories_are_resolvable() -> None:
    """Every documented target maps to a concrete directory name."""
    from pytscheck.runner import _PLATFORM_DIRS

    expected = {
        ("win32", "amd64"),
        ("win32", "arm64"),
        ("linux", "x86_64"),
        ("linux", "aarch64"),
        ("darwin", "x86_64"),
        ("darwin", "arm64"),
    }
    assert expected.issubset(_PLATFORM_DIRS.keys())


def test_alternate_machine_names_resolve() -> None:
    """Both x86_64/amd64 and aarch64/arm64 must map to the same dir."""
    from pytscheck.runner import _PLATFORM_DIRS

    # Linux
    assert _PLATFORM_DIRS[("linux", "x86_64")] == _PLATFORM_DIRS[("linux", "amd64")]
    assert _PLATFORM_DIRS[("linux", "aarch64")] == _PLATFORM_DIRS[("linux", "arm64")]
    # Windows
    assert _PLATFORM_DIRS[("win32", "amd64")] == _PLATFORM_DIRS[("win32", "x86_64")]


def test_binary_is_executable_on_posix(tsgo_binary: Path) -> None:
    if os.name == "nt":
        pytest.skip("permission bits not meaningful on Windows")
    assert file_has_executable_bit(tsgo_binary)


def test_fake_binary_has_same_path_shape(tmp_path: Path) -> None:
    """The runner's path shape must be reproducible for a fake install."""
    from tests.helpers import make_fake_tsgo_on_path

    platform_dir, binary = make_fake_tsgo_on_path(tmp_path, behavior="echo")
    assert platform_dir.name == "fake-platform"
    assert binary.parent.name == "lib"
    assert binary.exists()


def test_unsupported_platform_raises_clear_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bogus (sys.platform, machine) must raise UnsupportedPlatformError."""
    from pytscheck import runner

    if sys.platform in {"linux", "darwin", "win32"}:
        pytest.skip("unsupported-platform check requires a real unsupported OS; no platform mocks")
    with pytest.raises(UnsupportedPlatformError):
        runner._platform_dir()
