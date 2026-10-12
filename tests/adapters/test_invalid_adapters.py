"""Tests for adapters that violate the protocol."""

from __future__ import annotations

import pytest

from pytscheck.adapters.base import CompilerAdapter
from pytscheck.adapters.errors import (
    AdapterProtocolError,
    AdapterRegistrationError,
)
from pytscheck.adapters.registry import register_adapter
from pytscheck.adapters.sources import collect_sources
from pytscheck.models import SourceFile

# --- registration-time validation -------------------------------------------


def test_adapter_without_name_is_rejected() -> None:
    class NoName:
        def get_sources(self, project_root: str) -> list:
            return []

    with pytest.raises(AdapterProtocolError):
        register_adapter(NoName())  # type: ignore[arg-type]


def test_adapter_without_get_sources_is_rejected() -> None:
    class NoSources:
        @property
        def name(self) -> str:
            return "x"

    with pytest.raises(AdapterProtocolError):
        register_adapter(NoSources())  # type: ignore[arg-type]


def test_adapter_with_non_callable_get_sources_is_rejected() -> None:
    class Bad:
        @property
        def name(self) -> str:
            return "x"

        get_sources = "not callable"

    with pytest.raises(AdapterProtocolError):
        register_adapter(Bad())  # type: ignore[arg-type]


def test_adapter_with_empty_name_is_rejected() -> None:
    class Empty:
        @property
        def name(self) -> str:
            return ""

        def get_sources(self, project_root: str) -> list:
            return []

    with pytest.raises(AdapterRegistrationError, match="non-empty"):
        register_adapter(Empty())


# --- collection-time validation ---------------------------------------------


def test_adapter_returning_non_list_is_rejected() -> None:
    class ReturnsString:
        @property
        def name(self) -> str:
            return "x"

        def get_sources(self, project_root: str) -> list:
            return "not a list"  # type: ignore[return-value]

    # Iterating a string yields chars; those aren't SourceFiles
    with pytest.raises(AdapterProtocolError):
        collect_sources(ReturnsString(), "/")


def test_adapter_returning_none_is_rejected() -> None:
    class ReturnsNone:
        @property
        def name(self) -> str:
            return "x"

        def get_sources(self, project_root: str) -> list:
            return None  # type: ignore[return-value]

    with pytest.raises((AdapterProtocolError, TypeError)):
        collect_sources(ReturnsNone(), "/")


def test_adapter_raising_unexpected_exception_is_wrapped() -> None:
    """The api layer wraps non-Adapter exceptions; collect_sources itself
    does not, but the adapter's exception propagates as-is."""

    class Exploding:
        @property
        def name(self) -> str:
            return "boom"

        def get_sources(self, project_root: str) -> list:
            raise RuntimeError("internal bug in the adapter")

    # collect_sources lets it propagate; the api layer wraps it.
    with pytest.raises(RuntimeError):
        collect_sources(Exploding(), "/")


def test_adapter_raising_adapter_extraction_error_propagates() -> None:
    from pytscheck.adapters.errors import AdapterExtractionError

    class Extractor:
        @property
        def name(self) -> str:
            return "x"

        def get_sources(self, project_root: str) -> list:
            raise AdapterExtractionError("no script block")

    with pytest.raises(AdapterExtractionError):
        collect_sources(Extractor(), "/")


# --- duck-typing checks -----------------------------------------------------


def test_isinstance_check_rejects_objects_with_wrong_shape() -> None:
    class Wrong:
        pass

    assert not isinstance(Wrong(), CompilerAdapter)


def test_isinstance_check_accepts_correct_shape() -> None:
    class Right:
        @property
        def name(self) -> str:
            return "x"

        def get_sources(self, project_root: str) -> list:
            return []

    assert isinstance(Right(), CompilerAdapter)


# --- mixed-valid-and-invalid lists ------------------------------------------


def test_valid_then_invalid_sourcefile_rejected() -> None:
    class Mixed:
        @property
        def name(self) -> str:
            return "x"

        def get_sources(self, project_root: str) -> list:
            return [
                SourceFile(path="a.ts", text=""),
                "not a SourceFile",
            ]

    with pytest.raises(AdapterProtocolError):
        collect_sources(Mixed(), "/")


def test_valid_and_valid_sources_pass() -> None:
    class Good:
        @property
        def name(self) -> str:
            return "x"

        def get_sources(self, project_root: str) -> list:
            return [
                SourceFile(path="a.ts", text=""),
                SourceFile(path="b.ts", text=""),
            ]

    assert len(collect_sources(Good(), "/")) == 2
