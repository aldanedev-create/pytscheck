"""Integration test: an adapter for a component framework format.

Mimics a single-file-component tool (`.sfc`) that has `<template>` and
`<script>` blocks. The adapter extracts the script and hands it to
pytscheck.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pytscheck import check_project
from pytscheck.adapters.errors import AdapterExtractionError
from pytscheck.adapters.source_maps import remap_diagnostics
from pytscheck.adapters.sources import collect_sources
from pytscheck.checker import check_sources_virtual
from pytscheck.models import SourceFile

_SCRIPT_RE = re.compile(r"<script[^>]*>(?P<body>.*?)</script>", re.DOTALL)


class _SfcAdapter:
    @property
    def name(self) -> str:
        return "sfc-test"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        root = Path(project_root)
        if not root.is_dir():
            raise AdapterExtractionError(f"not a directory: {project_root}")
        sources: list[SourceFile] = []
        for sfc in sorted(root.rglob("*.sfc")):
            text = sfc.read_text(encoding="utf-8")
            m = _SCRIPT_RE.search(text)
            if m is None:
                raise AdapterExtractionError(f"no <script> in {sfc.name}")
            body = m.group("body")
            # Count offset lines so remapping can be approximate but honest
            offset_lines = text[: m.start("body")].count("\n")
            rel = sfc.relative_to(root)
            sources.append(
                SourceFile(
                    path=f"__sfc__/{rel}.ts",
                    text=body,
                    origin_path=str(rel),
                    kind="generated",
                    options={"offset_lines": offset_lines},
                )
            )
        return sources


def test_sfc_extraction(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "App.sfc").write_text(
        "<template><div>Hello</div></template>\n"
        "<script>\n"
        "export const greeting: string = 'hi';\n"
        "</script>\n",
        encoding="utf-8",
    )
    sources = collect_sources(_SfcAdapter(), str(tmp_path))
    assert len(sources) == 1
    assert sources[0].origin_path == "App.sfc"
    assert "greeting" in sources[0].text


def test_sfc_clean_check(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "App.sfc").write_text(
        "<template></template>\n<script>export const x: number = 1;</script>\n",
        encoding="utf-8",
    )
    sources = collect_sources(_SfcAdapter(), str(tmp_path))
    r = check_sources_virtual(sources)
    assert r.success, [d.message for d in r.errors]


def test_sfc_with_type_error(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "App.sfc").write_text(
        "<template></template>\n<script>export const x: number = 'bad';</script>\n",
        encoding="utf-8",
    )
    sources = collect_sources(_SfcAdapter(), str(tmp_path))
    r = check_sources_virtual(sources)
    assert not r.success
    assert any(d.code == 2322 for d in r.errors)


def test_sfc_diagnostic_remaps_to_sfc(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "App.sfc").write_text(
        "<template></template>\n<script>export const x: number = 'bad';</script>\n",
        encoding="utf-8",
    )
    sources = collect_sources(_SfcAdapter(), str(tmp_path))
    r = check_sources_virtual(sources)
    remapped = remap_diagnostics(r.diagnostics, sources)
    assert any(d.file == "App.sfc" for d in remapped)


def test_sfc_missing_script_raises(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "App.sfc").write_text("<template>Only template</template>\n")
    with pytest.raises(AdapterExtractionError, match="no <script>"):
        collect_sources(_SfcAdapter(), str(tmp_path))


def test_sfc_multiple_files(tsgo_binary, tmp_path: Path) -> None:
    for name in ("A.sfc", "B.sfc", "C.sfc"):
        (tmp_path / name).write_text(
            "<template></template>\n<script>export const n: number = 1;</script>\n",
            encoding="utf-8",
        )
    sources = collect_sources(_SfcAdapter(), str(tmp_path))
    assert len(sources) == 3


def test_sfc_via_public_api(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "App.sfc").write_text(
        "<template></template>\n<script>export const x: number = 'bad';</script>\n",
        encoding="utf-8",
    )
    r = check_project(tmp_path, adapter=_SfcAdapter())
    assert not r.success
    assert any(d.file == "App.sfc" for d in r.errors)


def test_sfc_clean_via_public_api(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "App.sfc").write_text(
        "<template></template>\n<script>export const x: number = 1;</script>\n",
        encoding="utf-8",
    )
    r = check_project(tmp_path, adapter=_SfcAdapter())
    assert r.success, [d.message for d in r.errors]
