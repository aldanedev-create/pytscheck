"""Tests for protocol-version compatibility between adapters and core."""

from __future__ import annotations

import pytest

from pytscheck.adapters.compatibility import check_protocol_version
from pytscheck.adapters.errors import AdapterProtocolError
from pytscheck.models import SourceFile
from pytscheck.version import ADAPTER_PROTOCOL_VERSION


class _Adapter:
    def __init__(self, version: object = None) -> None:
        if version is not None:
            self.protocol_version = version

    @property
    def name(self) -> str:
        return "test"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return []


# --- missing version --------------------------------------------------------


def test_no_version_attribute_is_accepted() -> None:
    check_protocol_version(_Adapter())


# --- matching versions ------------------------------------------------------


def test_matching_major_version_is_accepted() -> None:
    major, _minor = ADAPTER_PROTOCOL_VERSION.split(".")
    check_protocol_version(_Adapter(f"{major}.0"))


def test_matching_major_with_different_minor_is_accepted() -> None:
    major, _minor = ADAPTER_PROTOCOL_VERSION.split(".")
    check_protocol_version(_Adapter(f"{major}.99"))


def test_exact_version_is_accepted() -> None:
    check_protocol_version(_Adapter(ADAPTER_PROTOCOL_VERSION))


# --- mismatched versions ----------------------------------------------------


def test_mismatched_major_version_is_rejected() -> None:
    major, _minor = ADAPTER_PROTOCOL_VERSION.split(".")
    other = str(int(major) + 1)
    with pytest.raises(AdapterProtocolError, match="speaks protocol"):
        check_protocol_version(_Adapter(f"{other}.0"))


def test_older_major_version_is_rejected() -> None:
    major, _minor = ADAPTER_PROTOCOL_VERSION.split(".")
    if int(major) == 0:
        pytest.skip("no older major version")
    with pytest.raises(AdapterProtocolError):
        check_protocol_version(_Adapter(f"{int(major) - 1}.0"))


# --- malformed versions -----------------------------------------------------


def test_non_string_version_is_rejected() -> None:
    with pytest.raises(AdapterProtocolError, match="non-string"):
        check_protocol_version(_Adapter(1))


def test_none_version_falls_through() -> None:
    """None is treated as 'not declared', which is accepted."""
    check_protocol_version(_Adapter(None))


def test_empty_string_version_is_rejected() -> None:
    # "" splits to [""], whose major is "", which != current major
    with pytest.raises(AdapterProtocolError):
        check_protocol_version(_Adapter(""))


def test_version_without_dot_is_rejected() -> None:
    # "1" has major "1"; only accepted if current major is 1
    major, _ = ADAPTER_PROTOCOL_VERSION.split(".")
    if major == "1":
        check_protocol_version(_Adapter("1"))
    else:
        with pytest.raises(AdapterProtocolError):
            check_protocol_version(_Adapter("1"))


# --- version integration ----------------------------------------------------


def test_protocol_version_is_major_minor() -> None:
    parts = ADAPTER_PROTOCOL_VERSION.split(".")
    assert len(parts) == 2
    assert all(p.isdigit() for p in parts)


def test_protocol_version_major_is_positive() -> None:
    major, _ = ADAPTER_PROTOCOL_VERSION.split(".")
    assert int(major) >= 1
