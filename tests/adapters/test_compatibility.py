"""Tests for adapter protocol-version compatibility."""

from __future__ import annotations

import pytest

from pytscheck.adapters.compatibility import check_protocol_version
from pytscheck.adapters.errors import AdapterProtocolError
from pytscheck.models import SourceFile


class _Adapter:
    def __init__(self, version: object = None) -> None:
        if version is not None:
            self.protocol_version = version

    @property
    def name(self) -> str:
        return "test"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return []


def test_missing_version_is_accepted() -> None:
    check_protocol_version(_Adapter())


def test_matching_major_version_is_accepted() -> None:
    check_protocol_version(_Adapter("1.5"))


def test_mismatched_major_version_is_rejected() -> None:
    with pytest.raises(AdapterProtocolError, match="speaks protocol"):
        check_protocol_version(_Adapter("99.0"))


def test_non_string_version_is_rejected() -> None:
    with pytest.raises(AdapterProtocolError, match="non-string"):
        check_protocol_version(_Adapter(1))