"""Tests that the bundled binary's permissions are correct and enforced."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from pytscheck.exceptions import CompilerNotFoundError
from pytscheck.runner import binary_path
from tests.helpers import file_has_executable_bit, make_fake_tsgo


def test_bundled_binary_has_executable_bit(tsgo_binary: Path) -> None:
    if os.name == "nt":
        pytest.skip("permission bits not meaningful on Windows")
    assert file_has_executable_bit(tsgo_binary)


def test_bundled_binary_owner_readable(tsgo_binary: Path) -> None:
    if os.name == "nt":
        pytest.skip("permission bits not meaningful on Windows")
    mode = tsgo_binary.stat().st_mode
    assert mode & stat.S_IRUSR


def test_bundled_binary_is_a_regular_file(tsgo_binary: Path) -> None:
    assert tsgo_binary.is_file()
    assert not tsgo_binary.is_symlink() or tsgo_binary.resolve().is_file()


def test_binary_path_raises_if_not_executable() -> None:
    if os.name == "nt":
        pytest.skip("permission bits not meaningful on Windows")
    try:
        binary = binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    original = binary.stat().st_mode
    binary.chmod(0o644)
    try:
        with pytest.raises(CompilerNotFoundError, match="not executable"):
            binary_path()
    finally:
        binary.chmod(original)


def test_binary_path_returns_after_restoring_permissions() -> None:
    if os.name == "nt":
        pytest.skip("permission bits not meaningful on Windows")
    try:
        binary = binary_path()
    except CompilerNotFoundError:
        pytest.skip("no bundled binary present")

    original = binary.stat().st_mode
    binary.chmod(0o644)
    try:
        with pytest.raises(CompilerNotFoundError):
            binary_path()
    finally:
        binary.chmod(original)

    # After restore, binary_path must work again.
    assert binary_path() == binary


def test_fake_binary_is_executable_on_posix(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("permission bits not meaningful on Windows")
    binary = make_fake_tsgo(tmp_path / "lib" / "tsgo", behavior="echo")
    assert file_has_executable_bit(binary)


def test_fake_binary_reads_back_as_executable(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("permission bits not meaningful on Windows")
    binary = make_fake_tsgo(tmp_path / "lib" / "tsgo", behavior="echo")
    mode = binary.stat().st_mode
    assert mode & stat.S_IXUSR