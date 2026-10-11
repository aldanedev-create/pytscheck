"""Unit tests for the adapter protocol validation."""

from __future__ import annotations

import pytest

from pytscheck.adapters.base import CompilerAdapter
from pytscheck.adapters.errors import AdapterProtocolError
from pytscheck.adapters.registry import register_adapter, unregister_adapter
from pytscheck.adapters.sources import collect_sources
from pytscheck.models import SourceFile


class _Adapter:
    def __init__(self, name: str = "test", sources: list | None = None) -> None:
        self._name = name
        self._sources = sources if sources is not None else []

    @property
    def name(self) -> str:
        return self._name

    def get_sources(self, project_root: str) -> list:
        return self._sources


@pytest.fixture(autouse=True)
def _clean_registry():
    from pytscheck.adapters.registry import registered_adapters

    for name in list(registered_adapters()):
        unregister_adapter(name)
    yield
    for name in list(registered_adapters()):
        unregister_adapter(name)


# --- protocol conformance ---------------------------------------------------


def test_well_formed_adapter_satisfies_protocol() -> None:
    assert isinstance(_Adapter(), CompilerAdapter)


def test_object_without_name_does_not_satisfy_protocol() -> None:
    class NoName:
        def get_sources(self, project_root: str) -> list:
            return []

    assert not isinstance(NoName(), CompilerAdapter)


def test_object_without_get_sources_does_not_satisfy_protocol() -> None:
    class NoSources:
        @property
        def name(self) -> str:
            return "x"

    assert not isinstance(NoSources(), CompilerAdapter)


# --- registration -----------------------------------------------------------


def test_registration_succeeds_with_valid_adapter() -> None:
    register_adapter(_Adapter("a"))


def test_registration_rejects_non_adapter() -> None:
    class NotAnAdapter:
        pass

    with pytest.raises(AdapterProtocolError):
        register_adapter(NotAnAdapter())  # type: ignore[arg-type]


def test_registration_rejects_empty_name() -> None:
    from pytscheck.adapters.errors import AdapterRegistrationError

    with pytest.raises(AdapterRegistrationError, match="non-empty"):
        register_adapter(_Adapter(""))


def test_registration_rejects_duplicate_name() -> None:
    from pytscheck.adapters.errors import AdapterRegistrationError

    register_adapter(_Adapter("dup"))
    with pytest.raises(AdapterRegistrationError, match="already registered"):
        register_adapter(_Adapter("dup"))


# --- source collection ------------------------------------------------------


def test_collect_sources_returns_tuple() -> None:
    a = _Adapter(sources=[SourceFile(path="a.ts", text="")])
    out = collect_sources(a, "/")
    assert isinstance(out, tuple)
    assert len(out) == 1


def test_collect_sources_empty_ok() -> None:
    a = _Adapter(sources=[])
    assert collect_sources(a, "/") == ()


def test_collect_sources_rejects_non_sourcefile() -> None:
    a = _Adapter(sources=["not a sourcefile"])
    with pytest.raises(AdapterProtocolError):
        collect_sources(a, "/")


def test_collect_sources_rejects_empty_path() -> None:
    a = _Adapter(sources=[SourceFile(path="", text="x")])
    with pytest.raises(AdapterProtocolError, match="empty path"):
        collect_sources(a, "/")


def test_collect_sources_rejects_duplicate_paths() -> None:
    a = _Adapter(
        sources=[
            SourceFile(path="a.ts", text="1"),
            SourceFile(path="a.ts", text="2"),
        ]
    )
    with pytest.raises(AdapterProtocolError, match="duplicate"):
        collect_sources(a, "/")


def test_collect_sources_accepts_generated_kind() -> None:
    a = _Adapter(
        sources=[
            SourceFile(
                path="App.vel.ts",
                text="",
                origin_path="App.vel",
                kind="generated",
            )
        ]
    )
    out = collect_sources(a, "/")
    assert out[0].kind == "generated"