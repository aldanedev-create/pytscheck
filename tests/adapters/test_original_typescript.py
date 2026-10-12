"""Tests for adapters that pass through original TypeScript (kind='source')."""

from __future__ import annotations

from pathlib import Path

from pytscheck import checker
from pytscheck.adapters.sources import collect_sources
from pytscheck.models import SourceFile


class _PassthroughAdapter:
    def __init__(self, sources: list[SourceFile]) -> None:
        self._sources = sources

    @property
    def name(self) -> str:
        return "passthrough"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return self._sources


def test_source_kind_is_default() -> None:
    s = SourceFile(path="a.ts", text="export const x = 1;")
    assert s.kind == "source"


def test_original_source_check(tsgo_binary: Path) -> None:
    s = SourceFile(path="a.ts", text="export const x: number = 1;\n")
    sources = collect_sources(_PassthroughAdapter([s]), "/")
    r = checker.check_sources_virtual(sources)
    assert r.success


def test_original_source_with_error(tsgo_binary: Path) -> None:
    s = SourceFile(path="a.ts", text='export const x: number = "bad";\n')
    sources = collect_sources(_PassthroughAdapter([s]), "/")
    r = checker.check_sources_virtual(sources)
    assert not r.success


def test_original_source_without_origin_reports_virtual_path(tsgo_binary: Path) -> None:
    s = SourceFile(path="a.ts", text='export const x: number = "bad";\n')
    sources = collect_sources(_PassthroughAdapter([s]), "/")
    r = checker.check_sources_virtual(sources)
    assert any(d.file == "a.ts" for d in r.errors)


def test_original_source_with_origin_is_remappable(tsgo_binary: Path) -> None:
    from pytscheck.adapters.source_maps import remap_diagnostics

    s = SourceFile(
        path="a.ts",
        text='export const x: number = "bad";\n',
        origin_path="original.ts",
    )
    sources = collect_sources(_PassthroughAdapter([s]), "/")
    r = checker.check_sources_virtual(sources)
    remapped = remap_diagnostics(r.diagnostics, sources)
    assert any(d.file == "original.ts" for d in remapped)
    assert all(d.origin_file == "a.ts" for d in remapped if d.file == "original.ts")


def test_multiple_original_sources(tsgo_binary: Path) -> None:
    sources = [
        SourceFile(path="a.ts", text="export const a: number = 1;\n"),
        SourceFile(path="b.ts", text="export const b: string = 'x';\n"),
    ]
    collected = collect_sources(_PassthroughAdapter(sources), "/")
    r = checker.check_sources_virtual(collected)
    assert r.success


def test_original_sources_preserve_order(tsgo_binary: Path) -> None:
    sources = [
        SourceFile(path="c.ts", text="export const c: number = 3;\n"),
        SourceFile(path="a.ts", text="export const a: number = 1;\n"),
        SourceFile(path="b.ts", text="export const b: number = 2;\n"),
    ]
    collected = collect_sources(_PassthroughAdapter(sources), "/")
    assert [s.path for s in collected] == ["c.ts", "a.ts", "b.ts"]


def test_original_unicode_content(tsgo_binary: Path) -> None:
    s = SourceFile(path="a.ts", text='export const s: string = "héllo 世界";\n')
    sources = collect_sources(_PassthroughAdapter([s]), "/")
    r = checker.check_sources_virtual(sources)
    assert r.success
