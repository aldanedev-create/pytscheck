"""Tests for the CompilerAdapter protocol."""

from __future__ import annotations

import inspect

import pytest

from pytscheck.adapters.base import CompilerAdapter
from pytscheck.models import SourceFile


# --- structural conformance -------------------------------------------------


class _FullAdapter:
    @property
    def name(self) -> str:
        return "full"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return []


class _NoName:
    def get_sources(self, project_root: str) -> list[SourceFile]:
        return []


class _NoGetSources:
    @property
    def name(self) -> str:
        return "x"


class _NameIsMethodNotProperty:
    def name(self) -> str:
        return "x"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return []


def test_full_adapter_satisfies_protocol() -> None:
    assert isinstance(_FullAdapter(), CompilerAdapter)


def test_adapter_without_name_does_not_satisfy_protocol() -> None:
    assert not isinstance(_NoName(), CompilerAdapter)


def test_adapter_without_get_sources_does_not_satisfy_protocol() -> None:
    assert not isinstance(_NoGetSources(), CompilerAdapter)


def test_adapter_with_method_name_not_property_fails() -> None:
    """`name` must be a property, not a method."""
    assert not isinstance(_NameIsMethodNotProperty(), CompilerAdapter)


# --- explicit subclassing ---------------------------------------------------


def test_explicit_subclass_also_works() -> None:
    class Explicit(CompilerAdapter):
        @property
        def name(self) -> str:
            return "explicit"

        def get_sources(self, project_root: str) -> list[SourceFile]:
            return []

    assert isinstance(Explicit(), CompilerAdapter)


# --- runtime checkability ---------------------------------------------------


def test_protocol_is_runtime_checkable() -> None:
    # runtime_checkable protocols have a __protocol_attrs__ attribute
    assert hasattr(CompilerAdapter, "__protocol_attrs__")
    assert "name" in CompilerAdapter.__protocol_attrs__
    assert "get_sources" in CompilerAdapter.__protocol_attrs__


# --- method signatures ------------------------------------------------------


def test_get_sources_signature() -> None:
    sig = inspect.signature(CompilerAdapter.get_sources)
    assert list(sig.parameters) == ["self", "project_root"]


def test_name_is_property() -> None:
    prop = inspect.getattr_static(CompilerAdapter, "name")
    assert isinstance(prop, property)


# --- docstrings -------------------------------------------------------------


def test_protocol_has_docstring() -> None:
    assert inspect.getdoc(CompilerAdapter)


def test_get_sources_has_docstring() -> None:
    assert inspect.getdoc(CompilerAdapter.get_sources)