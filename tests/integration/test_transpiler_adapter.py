"""Integration test: an adapter that transpiles from a non-TS format.

Mimics a real consuming tool: takes a simplified "DSL" file, converts it
to TypeScript, and hands it to pytscheck.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import check_project
from pytscheck.adapters.errors import AdapterExtractionError
from pytscheck.adapters.source_maps import remap_diagnostics
from pytscheck.adapters.sources import collect_sources
from pytscheck.checker import check_sources_virtual
from pytscheck.models import SourceFile

# ---------------------------------------------------------------------------
# A tiny DSL that transpiles to TypeScript
# ---------------------------------------------------------------------------


def _transpile_dsl(text: str) -> str:
    """Translate a `.dsl` file to TypeScript.

    DSL syntax:
        let x: number = 1
        fn add(a: number, b: number): number => a + b
    """
    out: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("let "):
            out.append(f"export const {line[4:]};")
        elif line.startswith("fn "):
            rest = line[3:]
            name_params, body = rest.split("=>", 1)
            name_params = name_params.strip()
            if "(" in name_params:
                name, params = name_params.split("(", 1)
                params = "(" + params
            else:
                name, params = name_params, "()"
            out.append(f"export function {name.strip()}{params} {{ return {body.strip()}; }}")
        else:
            raise AdapterExtractionError(f"cannot parse DSL line: {line!r}")
    return "\n".join(out) + "\n"


class _DslAdapter:
    @property
    def name(self) -> str:
        return "dsl-test"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        root = Path(project_root)
        if not root.is_dir():
            raise AdapterExtractionError(f"not a directory: {project_root}")
        sources: list[SourceFile] = []
        for dsl in sorted(root.rglob("*.dsl")):
            text = dsl.read_text(encoding="utf-8")
            try:
                ts = _transpile_dsl(text)
            except AdapterExtractionError:
                raise
            rel = dsl.relative_to(root)
            sources.append(
                SourceFile(
                    path=f"__dsl__/{rel}.ts",
                    text=ts,
                    origin_path=str(rel),
                    kind="generated",
                )
            )
        return sources


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dsl_transpiles_clean(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "a.dsl").write_text(
        "let x: number = 1\nfn add(a: number, b: number): number => a + b\n",
        encoding="utf-8",
    )
    sources = collect_sources(_DslAdapter(), str(tmp_path))
    r = check_sources_virtual(sources)
    assert r.success, [d.message for d in r.errors]


def test_dsl_with_type_error(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "a.dsl").write_text('let x: number = "string"\n', encoding="utf-8")
    sources = collect_sources(_DslAdapter(), str(tmp_path))
    r = check_sources_virtual(sources)
    assert not r.success
    assert any(d.code == 2322 for d in r.errors)


def test_dsl_diagnostics_remap_to_origin(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "a.dsl").write_text('let x: number = "string"\n', encoding="utf-8")
    sources = collect_sources(_DslAdapter(), str(tmp_path))
    r = check_sources_virtual(sources)
    remapped = remap_diagnostics(r.diagnostics, sources)
    assert any(d.file == "a.dsl" for d in remapped)


def test_dsl_invalid_line_raises_extraction_error(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "bad.dsl").write_text("this is not a valid DSL line\n", encoding="utf-8")
    with pytest.raises(AdapterExtractionError, match="cannot parse DSL"):
        collect_sources(_DslAdapter(), str(tmp_path))


def test_dsl_project_via_public_api(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "a.dsl").write_text("let x: number = 1\n", encoding="utf-8")
    r = check_project(tmp_path, adapter=_DslAdapter())
    assert r.success


def test_dsl_project_error_via_public_api(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "a.dsl").write_text('let x: number = "s"\n', encoding="utf-8")
    r = check_project(tmp_path, adapter=_DslAdapter())
    assert not r.success
    assert any(d.file == "a.dsl" for d in r.errors)
