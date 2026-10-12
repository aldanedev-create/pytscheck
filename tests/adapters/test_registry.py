"""Tests for the adapter registry."""

from __future__ import annotations

import pytest

from pytscheck.adapters.errors import (
    AdapterProtocolError,
    AdapterRegistrationError,
)
from pytscheck.adapters.registry import (
    get_adapter,
    register_adapter,
    registered_adapters,
    unregister_adapter,
)
from pytscheck.models import SourceFile


class _Adapter:
    def __init__(self, name: str = "test") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return []


# --- registration -----------------------------------------------------------


def test_register_and_get_returns_same_instance() -> None:
    a = _Adapter("foo")
    register_adapter(a)
    assert get_adapter("foo") is a


def test_register_two_distinct_adapters() -> None:
    a = _Adapter("a")
    b = _Adapter("b")
    register_adapter(a)
    register_adapter(b)
    assert get_adapter("a") is a
    assert get_adapter("b") is b


def test_double_registration_raises() -> None:
    register_adapter(_Adapter("dup"))
    with pytest.raises(AdapterRegistrationError, match="already registered"):
        register_adapter(_Adapter("dup"))


def test_registration_of_non_adapter_raises() -> None:
    class NotAnAdapter:
        pass

    with pytest.raises(AdapterProtocolError):
        register_adapter(NotAnAdapter())  # type: ignore[arg-type]


def test_registration_with_empty_name_raises() -> None:
    with pytest.raises(AdapterRegistrationError, match="non-empty"):
        register_adapter(_Adapter(""))


def test_registration_with_whitespace_only_name_raises() -> None:
    with pytest.raises(AdapterRegistrationError, match="non-empty"):
        register_adapter(_Adapter("   "))


# --- lookup -----------------------------------------------------------------


def test_get_missing_adapter_raises() -> None:
    with pytest.raises(AdapterRegistrationError, match="no adapter registered"):
        get_adapter("never-registered")


# --- unregistration ---------------------------------------------------------


def test_unregister_removes_adapter() -> None:
    register_adapter(_Adapter("gone"))
    unregister_adapter("gone")
    with pytest.raises(AdapterRegistrationError):
        get_adapter("gone")


def test_unregister_missing_is_noop() -> None:
    unregister_adapter("never-registered")  # must not raise


def test_unregister_then_reregister_works() -> None:
    register_adapter(_Adapter("re"))
    unregister_adapter("re")
    register_adapter(_Adapter("re"))
    assert get_adapter("re").name == "re"


# --- listing ----------------------------------------------------------------


def test_registered_adapters_empty() -> None:
    assert registered_adapters() == ()


def test_registered_adapters_sorted() -> None:
    for name in ("c", "a", "b"):
        register_adapter(_Adapter(name))
    assert registered_adapters() == ("a", "b", "c")


def test_registered_adapters_returns_tuple() -> None:
    assert isinstance(registered_adapters(), tuple)


def test_registered_adapters_reflects_additions() -> None:
    assert registered_adapters() == ()
    register_adapter(_Adapter("x"))
    assert registered_adapters() == ("x",)
    register_adapter(_Adapter("y"))
    assert registered_adapters() == ("x", "y")


# --- isolation between tests ------------------------------------------------


def test_registry_starts_empty() -> None:
    """The autouse fixture must have cleared the registry."""
    assert registered_adapters() == ()
