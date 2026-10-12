"""Tests for adapters that return no sources or fail to find sources."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck.adapters.errors import (
    AdapterError,
    AdapterExtractionError,
    AdapterProtocolError,
)
from pytscheck.adapters.sources import collect_sources
from pytscheck.exceptions import ConfigurationError
from pytscheck.models import SourceFile


class _EmptyAdapter:
    @property
    def name(self) -> str:
        return "empty"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return []


class _MissingDirAdapter:
    @property
    def name(self) -> str:
        return "missing"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        if not Path(project_root).exists():
            raise AdapterExtractionError(f"project not found: {project_root}")
        return []


# --- empty source lists -----------------------------------------------------


def test_empty_source_list_is_allowed_by_collect() -> None:
    out = collect_sources(_EmptyAdapter(), "/")
    assert out == ()


def test_empty_source_list_is_rejected_by_checker() -> None:
    from pytscheck.checker import check_sources_virtual

    with pytest.raises(ConfigurationError, match="no sources"):
        check_sources_virtual(())


# --- missing project root ---------------------------------------------------


def test_missing_project_raises_extraction_error() -> None:
    with pytest.raises(AdapterExtractionError, match="project not found"):
        collect_sources(_MissingDirAdapter(), "/does/not/exist")


def test_missing_project_is_adapter_error_subclass() -> None:
    with pytest.raises(AdapterError):
        collect_sources(_MissingDirAdapter(), "/does/not/exist")


# --- extraction vs type errors ----------------------------------------------


def test_extraction_error_is_not_a_diagnostic() -> None:
    from pytscheck.models import Diagnostic

    assert not issubclass(AdapterExtractionError, Diagnostic)


def test_extraction_error_is_not_a_protocol_error() -> None:
    assert not issubclass(AdapterExtractionError, AdapterProtocolError)


# --- empty after filtering --------------------------------------------------


def test_adapter_filters_out_everything() -> None:
    class FiltersAll:
        @property
        def name(self) -> str:
            return "filter"

        def get_sources(self, project_root: str) -> list[SourceFile]:
            # Adapter decides nothing is worth checking.
            return []

    out = collect_sources(FiltersAll(), "/")
    assert out == ()


# --- null-handling ----------------------------------------------------------


def test_adapter_returning_none_raises() -> None:
    class NoneAdapter:
        @property
        def name(self) -> str:
            return "none"

        def get_sources(self, project_root: str) -> list[SourceFile]:
            return None  # type: ignore[return-value]

    with pytest.raises((AdapterProtocolError, TypeError)):
        collect_sources(NoneAdapter(), "/")
