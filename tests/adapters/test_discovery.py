"""Tests for entry-point adapter discovery.

Discovery reads importlib.metadata entry points. In the test environment
with no registered entry points under `pytscheck.adapters`, discovery is
a no-op. We test the API contract and the failure modes we can control.
"""

from __future__ import annotations

import pytest

from pytscheck.adapters.discovery import discover_adapters
from pytscheck.adapters.errors import AdapterDiscoveryError
from pytscheck.adapters.registry import registered_adapters
from pytscheck.defaults import DEFAULT_ADAPTER_ENTRY_POINT_GROUP


def test_discovery_returns_tuple() -> None:
    result = discover_adapters()
    assert isinstance(result, tuple)


def test_discovery_empty_group_returns_empty() -> None:
    result = discover_adapters("pytscheck.nonexistent.group")
    assert result == ()


def test_discovery_default_group_is_the_declared_one() -> None:
    assert DEFAULT_ADAPTER_ENTRY_POINT_GROUP == "pytscheck.adapters"


def test_discovery_registers_found_adapters() -> None:
    """Whatever discovery returns must also be registered."""
    found = discover_adapters()
    for name in found:
        assert name in registered_adapters()


def test_discovery_is_idempotent_when_no_adapters() -> None:
    """Calling discovery twice must not raise if no adapters are installed."""
    a = discover_adapters()
    b = discover_adapters()
    assert a == b == ()


def test_discovery_with_bogus_group_does_not_raise() -> None:
    """A group with no entry points is not an error."""
    assert discover_adapters("this.group.does.not.exist.anywhere") == ()


def test_discovery_preserves_registry_state() -> None:
    """Discovery must not clobber pre-registered adapters (unless collision)."""
    # Register a custom adapter first
    from pytscheck.adapters.registry import get_adapter, register_adapter
    from pytscheck.models import SourceFile

    class _Custom:
        @property
        def name(self) -> str:
            return "my-custom-test"

        def get_sources(self, project_root: str) -> list[SourceFile]:
            return []

    register_adapter(_Custom())
    discover_adapters()
    assert get_adapter("my-custom-test").name == "my-custom-test"