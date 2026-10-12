"""Tests for adapters that return duplicate source paths."""

from __future__ import annotations

import pytest

from pytscheck.adapters.errors import AdapterProtocolError
from pytscheck.adapters.sources import collect_sources
from pytscheck.models import SourceFile


class _Adapter:
    def __init__(self, sources: list[SourceFile]) -> None:
        self._sources = sources

    @property
    def name(self) -> str:
        return "dup"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return self._sources


def test_two_same_paths_rejected() -> None:
    a = _Adapter(
        [
            SourceFile(path="a.ts", text="1"),
            SourceFile(path="a.ts", text="2"),
        ]
    )
    with pytest.raises(AdapterProtocolError, match="duplicate"):
        collect_sources(a, "/")


def test_three_same_paths_rejected() -> None:
    a = _Adapter(
        [
            SourceFile(path="a.ts", text="1"),
            SourceFile(path="b.ts", text=""),
            SourceFile(path="a.ts", text="2"),
        ]
    )
    with pytest.raises(AdapterProtocolError, match="duplicate"):
        collect_sources(a, "/")


def test_same_content_different_paths_ok() -> None:
    a = _Adapter(
        [
            SourceFile(path="a.ts", text="same content"),
            SourceFile(path="b.ts", text="same content"),
        ]
    )
    out = collect_sources(a, "/")
    assert len(out) == 2


def test_same_origin_path_but_different_virtual_paths_ok() -> None:
    """Two virtual files may map to the same origin (e.g., split script)."""
    a = _Adapter(
        [
            SourceFile(path="App.a.ts", text="", origin_path="App.vel"),
            SourceFile(path="App.b.ts", text="", origin_path="App.vel"),
        ]
    )
    out = collect_sources(a, "/")
    assert len(out) == 2


def test_duplicate_error_message_names_path() -> None:
    a = _Adapter(
        [
            SourceFile(path="path/to/dup.ts", text=""),
            SourceFile(path="path/to/dup.ts", text=""),
        ]
    )
    with pytest.raises(AdapterProtocolError, match=r"path/to/dup\.ts"):
        collect_sources(a, "/")


def test_empty_paths_are_rejected_before_duplicates() -> None:
    a = _Adapter(
        [
            SourceFile(path="", text=""),
            SourceFile(path="", text=""),
        ]
    )
    # Empty path check comes first
    with pytest.raises(AdapterProtocolError, match="empty path"):
        collect_sources(a, "/")


def test_case_sensitive_duplicates() -> None:
    """Different case = different path in the check; the adapter is responsible
    for canonicalization if its platform is case-insensitive."""
    a = _Adapter(
        [
            SourceFile(path="App.ts", text=""),
            SourceFile(path="app.ts", text=""),
        ]
    )
    out = collect_sources(a, "/")
    assert len(out) == 2
