"""Tests for adapters that generate TypeScript (kind='generated')."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import checker
from pytscheck.adapters.errors import AdapterExtractionError
from pytscheck.adapters.source_maps import remap_diagnostics
from pytscheck.adapters.sources import collect_sources
from pytscheck.models import SourceFile


class _GeneratedAdapter:
    """Adapter that emits a fixed set of TypeScript sources."""

    def __init__(self, sources: list[SourceFile]) -> None:
        self._sources = sources

    @property
    def name(self) -> str:
        return "generated"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return self._sources


# --- end-to-end check -------------------------------------------------------


def test_generated_clean_compiles(tsgo_binary: Path) -> None:
    src = SourceFile(
        path="__gen__/a.ts",
        text="export const x: number = 1;\n",
        origin_path="App.vel",
        kind="generated",
    )
    sources = collect_sources(_GeneratedAdapter([src]), "/")
    r = checker.check_sources_virtual(sources)
    assert r.success


def test_generated_with_error_reports_diagnostic(tsgo_binary: Path) -> None:
    src = SourceFile(
        path="__gen__/a.ts",
        text='export const x: number = "bad";\n',
        origin_path="App.vel",
        kind="generated",
    )
    sources = collect_sources(_GeneratedAdapter([src]), "/")
    r = checker.check_sources_virtual(sources)
    assert not r.success
    assert any(d.code == 2322 for d in r.errors)


def test_generated_diagnostic_remaps_to_origin(tsgo_binary: Path) -> None:
    src = SourceFile(
        path="__gen__/a.ts",
        text='export const x: number = "bad";\n',
        origin_path="App.vel",
        kind="generated",
    )
    sources = collect_sources(_GeneratedAdapter([src]), "/")
    r = checker.check_sources_virtual(sources)
    remapped = remap_diagnostics(r.diagnostics, sources)
    assert any(d.file == "App.vel" for d in remapped)


def test_generated_multiple_files(tsgo_binary: Path) -> None:
    sources = [
        SourceFile(
            path="__gen__/a.ts",
            text="export const a: number = 1;\n",
            origin_path="A.vel",
            kind="generated",
        ),
        SourceFile(
            path="__gen__/b.ts",
            text="export const b: number = 2;\n",
            origin_path="B.vel",
            kind="generated",
        ),
    ]
    collected = collect_sources(_GeneratedAdapter(sources), "/")
    r = checker.check_sources_virtual(collected)
    assert r.success


def test_generated_with_source_map_valid(tsgo_binary: Path) -> None:
    src = SourceFile(
        path="__gen__/a.ts",
        text='export const x: number = "bad";\n',
        origin_path="App.vel",
        source_map='{"version": 3, "sources": [], "mappings": ""}',
        kind="generated",
    )
    sources = collect_sources(_GeneratedAdapter([src]), "/")
    r = checker.check_sources_virtual(sources)
    assert not r.success
    remapped = remap_diagnostics(r.diagnostics, sources)
    assert any(d.file == "App.vel" for d in remapped)


def test_generated_with_invalid_source_map_raises_on_remap() -> None:
    from pytscheck.adapters.errors import AdapterMappingError

    src = SourceFile(
        path="__gen__/a.ts",
        text="",
        origin_path="App.vel",
        source_map="not json",
        kind="generated",
    )
    d = Diagnostic_(
        file="__gen__/a.ts", line=1, column=1, code=1, category="error", message="m"
    )
    with pytest.raises(AdapterMappingError):
        remap_diagnostics((d,), (src,))


def test_generated_adapter_extraction_error(tmp_path: Path) -> None:
    class Failing:
        @property
        def name(self) -> str:
            return "failing"

        def get_sources(self, project_root: str) -> list[SourceFile]:
            raise AdapterExtractionError("malformed input")

    with pytest.raises(AdapterExtractionError):
        collect_sources(Failing(), str(tmp_path))


# --- helper for the invalid-source-map test ---------------------------------


def Diagnostic_(**kwargs):  # type: ignore[no-redef]
    from pytscheck.models import Diagnostic

    return Diagnostic(**kwargs)