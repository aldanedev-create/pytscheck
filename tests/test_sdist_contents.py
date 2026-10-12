"""Tests for the sdist contents."""

from __future__ import annotations

import tarfile
from pathlib import Path


def _sdist_members(sdist: Path) -> list[str]:
    with tarfile.open(sdist) as tf:
        return sorted(tf.getnames())


def test_sdist_is_valid_tarball(built_sdist: Path) -> None:
    members = _sdist_members(built_sdist)
    assert members


def test_sdist_contains_pyproject(built_sdist: Path) -> None:
    members = _sdist_members(built_sdist)
    assert any(m.endswith("/pyproject.toml") for m in members)


def test_sdist_contains_readme(built_sdist: Path) -> None:
    members = _sdist_members(built_sdist)
    assert any(m.endswith("/README.md") for m in members)


def test_sdist_contains_license(built_sdist: Path) -> None:
    members = _sdist_members(built_sdist)
    assert any(m.endswith("/LICENSE") for m in members)


def test_sdist_contains_notice(built_sdist: Path) -> None:
    members = _sdist_members(built_sdist)
    assert any(m.endswith("/NOTICE.txt") for m in members)


def test_sdist_contains_src(built_sdist: Path) -> None:
    members = _sdist_members(built_sdist)
    assert any("/src/pytscheck/__init__.py" in m for m in members)


def test_sdist_contains_tests(built_sdist: Path) -> None:
    members = _sdist_members(built_sdist)
    assert any("/tests/" in m for m in members)


def test_sdist_contains_scripts(built_sdist: Path) -> None:
    members = _sdist_members(built_sdist)
    assert any("/scripts/build_binaries.py" in m for m in members)


def test_sdist_contains_conformance(built_sdist: Path) -> None:
    members = _sdist_members(built_sdist)
    assert any("/conformance/" in m for m in members)


def test_sdist_contains_no_binaries(built_sdist: Path) -> None:
    """The sdist must not bundle platform binaries (they're fetched at build)."""
    members = _sdist_members(built_sdist)
    for m in members:
        assert not m.endswith("/tsgo"), m
        assert not m.endswith("/tsgo.exe"), m


def test_sdist_no_pycache(built_sdist: Path) -> None:
    members = _sdist_members(built_sdist)
    assert not any("__pycache__" in m for m in members)


def test_sdist_no_git_directory(built_sdist: Path) -> None:
    members = _sdist_members(built_sdist)
    assert not any("/.git/" in m for m in members)
