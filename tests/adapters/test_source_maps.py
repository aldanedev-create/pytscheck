"""Tests for source-map parsing and diagnostic remapping."""

from __future__ import annotations

import json

import pytest

from pytscheck.adapters.errors import AdapterMappingError
from pytscheck.adapters.source_maps import remap_diagnostics
from pytscheck.models import Diagnostic, SourceFile


def _d(file: str = "App.ts", line: int = 1, column: int = 1) -> Diagnostic:
    return Diagnostic(
        file=file, line=line, column=column, code=2322, category="error", message="m"
    )


def _valid_map() -> str:
    return json.dumps({"version": 3, "sources": [], "mappings": ""})


# --- happy paths ------------------------------------------------------------


def test_remap_uses_origin_path() -> None:
    src = SourceFile(
        path="App.vel.ts",
        text="",
        origin_path="App.vel",
        kind="generated",
    )
    out = remap_diagnostics((_d("App.vel.ts"),), (src,))
    assert out[0].file == "App.vel"
    assert out[0].origin_file == "App.vel.ts"


def test_remap_preserves_other_fields() -> None:
    src = SourceFile(
        path="a.ts", text="", origin_path="a.vel", kind="generated"
    )
    original = Diagnostic(
        file="a.ts", line=5, column=10, code=9999, category="warning", message="w"
    )
    out = remap_diagnostics((original,), (src,))
    assert out[0].line == 5
    assert out[0].column == 10
    assert out[0].code == 9999
    assert out[0].category == "warning"
    assert out[0].message == "w"


def test_remap_multiple_sources() -> None:
    s1 = SourceFile(path="a.ts", text="", origin_path="a.vel", kind="generated")
    s2 = SourceFile(path="b.ts", text="", origin_path="b.vel", kind="generated")
    out = remap_diagnostics((_d("a.ts"), _d("b.ts")), (s1, s2))
    assert out[0].file == "a.vel"
    assert out[1].file == "b.vel"


# --- no origin --------------------------------------------------------------


def test_remap_keeps_original_when_no_origin() -> None:
    src = SourceFile(path="App.ts", text="")
    out = remap_diagnostics((_d("App.ts"),), (src,))
    assert out[0].file == "App.ts"
    assert out[0].origin_file is None


def test_remap_leaves_unknown_file_untouched() -> None:
    src = SourceFile(path="App.ts", text="", origin_path="App.vel")
    out = remap_diagnostics((_d("other.ts"),), (src,))
    assert out[0].file == "other.ts"


def test_remap_leaves_global_diagnostic_untouched() -> None:
    src = SourceFile(path="App.ts", text="", origin_path="App.vel")
    g = Diagnostic(
        file=None, line=0, column=0, code=1000, category="error", message="global"
    )
    out = remap_diagnostics((g,), (src,))
    assert out[0].file is None
    assert out[0].origin_file is None


# --- source map validation --------------------------------------------------


def test_remap_accepts_valid_source_map() -> None:
    src = SourceFile(
        path="a.ts", text="", origin_path="a.vel", source_map=_valid_map()
    )
    out = remap_diagnostics((_d("a.ts"),), (src,))
    assert out[0].file == "a.vel"


def test_remap_rejects_malformed_json() -> None:
    src = SourceFile(
        path="a.ts", text="", origin_path="a.vel", source_map="not json"
    )
    with pytest.raises(AdapterMappingError, match="not valid JSON"):
        remap_diagnostics((_d("a.ts"),), (src,))


def test_remap_rejects_source_map_without_mappings() -> None:
    src = SourceFile(
        path="a.ts",
        text="",
        origin_path="a.vel",
        source_map='{"version": 3}',
    )
    with pytest.raises(AdapterMappingError, match="missing 'mappings'"):
        remap_diagnostics((_d("a.ts"),), (src,))


def test_remap_rejects_source_map_that_is_json_but_not_dict() -> None:
    src = SourceFile(
        path="a.ts",
        text="",
        origin_path="a.vel",
        source_map='"a string"',
    )
    with pytest.raises(AdapterMappingError):
        remap_diagnostics((_d("a.ts"),), (src,))


def test_remap_rejects_empty_source_map_string() -> None:
    src = SourceFile(
        path="a.ts", text="", origin_path="a.vel", source_map=""
    )
    with pytest.raises(AdapterMappingError):
        remap_diagnostics((_d("a.ts"),), (src,))


# --- empty inputs -----------------------------------------------------------


def test_remap_empty_diagnostics() -> None:
    assert remap_diagnostics((), ()) == ()


def test_remap_empty_sources() -> None:
    out = remap_diagnostics((_d("a.ts"),), ())
    assert out[0].file == "a.ts"


def test_remap_returns_tuple() -> None:
    out = remap_diagnostics((), ())
    assert isinstance(out, tuple)