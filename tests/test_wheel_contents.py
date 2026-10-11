"""Tests that the built wheel contains everything required to run offline."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.helpers import (
    list_wheel_members,
    read_manifest_json_from_wheel,
    read_metadata_from_wheel,
)


def _is_wheel_included(members: list[str], suffix: str) -> bool:
    return any(m.endswith(suffix) for m in members)


def test_wheel_contains_pytscheck_package(built_wheel: Path) -> None:
    members = list_wheel_members(built_wheel)
    assert any(m.startswith("pytscheck/") for m in members)


def test_wheel_contains_py_typed(built_wheel: Path) -> None:
    members = list_wheel_members(built_wheel)
    assert _is_wheel_included(members, "pytscheck/py.typed")


def test_wheel_contains_manifest_json(built_wheel: Path) -> None:
    members = list_wheel_members(built_wheel)
    assert _is_wheel_included(members, "pytscheck/bin/manifest.json")


def test_wheel_contains_license(built_wheel: Path) -> None:
    members = list_wheel_members(built_wheel)
    assert any(
        m.endswith("/LICENSE") or m.endswith(".dist-info/LICENSE")
        for m in members
    )


def test_wheel_contains_metadata(built_wheel: Path) -> None:
    members = list_wheel_members(built_wheel)
    assert any(".dist-info/METADATA" in m for m in members)


def test_wheel_contains_only_current_platform_bin(built_wheel: Path) -> None:
    """Each wheel must contain exactly one platform's tsgo binary."""
    members = list_wheel_members(built_wheel)
    binaries = [m for m in members if m.endswith("/tsgo") or m.endswith("/tsgo.exe")]
    if not binaries:
        pytest.skip(
            "no binary in wheel (Phase 0 not run for this platform)"
        )
    assert len(binaries) == 1, binaries


def test_wheel_manifest_is_valid_json(built_wheel: Path) -> None:
    manifest = read_manifest_json_from_wheel(built_wheel)
    assert "compiler_version" in manifest
    assert "platforms" in manifest


def test_wheel_metadata_lists_version(built_wheel: Path) -> None:
    metadata = read_metadata_from_wheel(built_wheel)
    assert "Name: pytscheck" in metadata
    assert "Version:" in metadata


def test_wheel_metadata_requires_python_311(built_wheel: Path) -> None:
    metadata = read_metadata_from_wheel(built_wheel)
    assert "Requires-Python: >=3.11" in metadata


def test_wheel_metadata_license(built_wheel: Path) -> None:
    metadata = read_metadata_from_wheel(built_wheel)
    assert "Apache" in metadata


def test_wheel_has_no_pycache(built_wheel: Path) -> None:
    members = list_wheel_members(built_wheel)
    assert not any("__pycache__" in m for m in members)


def test_wheel_has_no_pyc(built_wheel: Path) -> None:
    members = list_wheel_members(built_wheel)
    assert not any(m.endswith(".pyc") for m in members)


def test_wheel_no_test_files(built_wheel: Path) -> None:
    members = list_wheel_members(built_wheel)
    assert not any(m.startswith("tests/") for m in members)