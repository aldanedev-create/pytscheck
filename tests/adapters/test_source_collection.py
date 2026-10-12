"""Tests for source collection and validation."""

from __future__ import annotations

import pytest

from pytscheck.adapters.errors import AdapterProtocolError
from pytscheck.adapters.sources import collect_sources
from pytscheck.models import SourceFile


class _Adapter:
    def __init__(self, sources: list[object] | None = None) -> None:
        self._sources = sources if sources is not None else []

    @property
    def name(self) -> str:
        return "test"

    def get_sources(self, project_root: str) -> list:
        return self._sources


# --- happy paths ------------------------------------------------------------


def test_collect_returns_tuple() -> None:
    a = _Adapter([SourceFile(path="a.ts", text="")])
    assert isinstance(collect_sources(a, "/"), tuple)


def test_collect_empty_list() -> None:
    assert collect_sources(_Adapter([]), "/") == ()


def test_collect_single_source() -> None:
    s = SourceFile(path="a.ts", text="export const x = 1;")
    a = _Adapter([s])
    out = collect_sources(a, "/")
    assert out == (s,)


def test_collect_multiple_sources_preserves_order() -> None:
    sources = [
        SourceFile(path="a.ts", text=""),
        SourceFile(path="b.ts", text=""),
        SourceFile(path="c.ts", text=""),
    ]
    out = collect_sources(_Adapter(sources), "/")
    assert [s.path for s in out] == ["a.ts", "b.ts", "c.ts"]


def test_collect_passes_project_root() -> None:
    seen = []

    class _Recording:
        @property
        def name(self) -> str:
            return "rec"

        def get_sources(self, project_root: str) -> list[SourceFile]:
            seen.append(project_root)
            return []

    collect_sources(_Recording(), "/some/path")
    assert seen == ["/some/path"]


# --- validation -------------------------------------------------------------


def test_collect_rejects_non_sourcefile() -> None:
    a = _Adapter(["not a sourcefile"])
    with pytest.raises(AdapterProtocolError, match="non-SourceFile"):
        collect_sources(a, "/")


def test_collect_rejects_dict_in_list() -> None:
    a = _Adapter([{"path": "a.ts", "text": ""}])
    with pytest.raises(AdapterProtocolError, match="non-SourceFile"):
        collect_sources(a, "/")


def test_collect_rejects_empty_path() -> None:
    a = _Adapter([SourceFile(path="", text="x")])
    with pytest.raises(AdapterProtocolError, match="empty path"):
        collect_sources(a, "/")


def test_collect_rejects_duplicate_paths() -> None:
    a = _Adapter(
        [
            SourceFile(path="a.ts", text="1"),
            SourceFile(path="a.ts", text="2"),
        ]
    )
    with pytest.raises(AdapterProtocolError, match="duplicate"):
        collect_sources(a, "/")


def test_collect_rejects_duplicate_after_other_files() -> None:
    a = _Adapter(
        [
            SourceFile(path="a.ts", text=""),
            SourceFile(path="b.ts", text=""),
            SourceFile(path="a.ts", text=""),
        ]
    )
    with pytest.raises(AdapterProtocolError, match="duplicate"):
        collect_sources(a, "/")


def test_collect_rejects_non_string_path() -> None:
    a = _Adapter([SourceFile(path=123, text="")])  # type: ignore[arg-type]
    with pytest.raises(AdapterProtocolError):
        collect_sources(a, "/")


# --- preserves all SourceFile fields ----------------------------------------


def test_collect_preserves_origin_path() -> None:
    s = SourceFile(path="App.ts", text="", origin_path="App.vel")
    out = collect_sources(_Adapter([s]), "/")
    assert out[0].origin_path == "App.vel"


def test_collect_preserves_source_map() -> None:
    s = SourceFile(path="App.ts", text="", source_map='{"version":3,"mappings":""}')
    out = collect_sources(_Adapter([s]), "/")
    assert out[0].source_map == '{"version":3,"mappings":""}'


def test_collect_preserves_kind() -> None:
    s = SourceFile(path="App.ts", text="", kind="generated")
    out = collect_sources(_Adapter([s]), "/")
    assert out[0].kind == "generated"


def test_collect_preserves_options() -> None:
    s = SourceFile(path="App.ts", text="", options={"strict": True})
    out = collect_sources(_Adapter([s]), "/")
    assert out[0].options == {"strict": True}
