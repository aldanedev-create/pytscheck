"""Tests for pytscheck.version."""

from __future__ import annotations

import re

from pytscheck import version


def test_version_matches_pep440_prefix() -> None:
    # Accepts 0.1.0, 0.1.0.dev0, 1.2.3rc1, etc.
    assert re.match(r"^\d+\.\d+\.\d+([.-]?(dev|a|b|rc)\d*)?$", version.__version__)


def test_version_is_nonempty_string() -> None:
    assert isinstance(version.__version__, str)
    assert version.__version__


def test_compiler_version_pinned() -> None:
    assert version.COMPILER_VERSION
    assert version.COMPILER_VERSION.lower() not in {"latest", "*", "any"}


def test_compiler_version_looks_like_semver_with_prerelease() -> None:
    # e.g. 7.0.0-dev.20260707.2
    assert re.match(r"^\d+\.\d+\.\d+", version.COMPILER_VERSION)


def test_adapter_protocol_version_is_major_minor() -> None:
    assert re.match(r"^\d+\.\d+$", version.ADAPTER_PROTOCOL_VERSION)


def test_all_matches_contents() -> None:
    expected = {"__version__", "COMPILER_VERSION", "ADAPTER_PROTOCOL_VERSION"}
    assert set(version.__all__) == expected
    for name in version.__all__:
        assert hasattr(version, name)


def test_package_reexports_versions() -> None:
    import pytscheck

    assert pytscheck.__version__ == version.__version__
    assert pytscheck.COMPILER_VERSION == version.COMPILER_VERSION
    assert pytscheck.ADAPTER_PROTOCOL_VERSION == version.ADAPTER_PROTOCOL_VERSION
