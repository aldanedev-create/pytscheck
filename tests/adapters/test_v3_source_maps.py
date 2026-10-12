"""Source-map v3 coordinates, multi-source maps, and real diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pytscheck import Diagnostic, RelatedInformation, SourceFile, check_project
from pytscheck.adapters.source_maps import remap_diagnostics
from pytscheck.exceptions import AdapterMappingError

_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"


def vlq(*values: int) -> str:
    result = ""
    for value in values:
        number = (abs(value) << 1) | int(value < 0)
        while number >= 32:
            result += _CHARS[(number & 31) | 32]
            number >>= 5
        result += _CHARS[number]
    return result


def source(mappings: str, **extra) -> SourceFile:
    return SourceFile(
        "src/generated.ts",
        "",
        source_map=json.dumps(
            {
                "version": 3,
                "sources": ["original.vel"],
                "names": [],
                "mappings": mappings,
                **extra,
            }
        ),
    )


def diag(line: int, column: int) -> Diagnostic:
    return Diagnostic("src/generated.ts", line, column, 2322, "error", "type mismatch")


def test_multiline_deltas_and_related_positions() -> None:
    mapping = source(vlq(0, 0, 4, 2) + ";" + vlq(3, 0, 2, -1))
    diagnostic = diag(2, 4)
    diagnostic = Diagnostic(
        diagnostic.file,
        diagnostic.line,
        diagnostic.column,
        diagnostic.code,
        diagnostic.category,
        diagnostic.message,
        end_line=2,
        end_column=5,
        related=(RelatedInformation("src/generated.ts", 1, 1, "declared here"),),
    )
    result = remap_diagnostics((diagnostic,), (mapping,))[0]
    assert (result.file, result.line, result.column) == ("src/original.vel", 7, 2)
    assert (result.end_line, result.end_column) == (7, 2)
    assert (result.related[0].line, result.related[0].column) == (5, 3)


def test_multiple_sources_and_source_root() -> None:
    mapping = source(
        vlq(0, 0, 0, 0) + "," + vlq(5, 1, 4, 2),
        sources=["one.vel", "two.vel"],
        sourceRoot="../original",
    )
    first, second = remap_diagnostics((diag(1, 1), diag(1, 6)), (mapping,))
    assert first.file == "original/one.vel"
    assert (second.file, second.line, second.column) == ("original/two.vel", 5, 3)


def test_unmapped_segments_and_lines_retain_generated_location() -> None:
    mapping = source(vlq(0, 0, 0, 0) + "," + vlq(5))
    for diagnostic in [diag(1, 6), diag(2, 1)]:
        assert remap_diagnostics((diagnostic,), (mapping,))[0] == diagnostic


def test_indexed_sections_end_previous_coverage() -> None:
    inner = {"version": 3, "sources": ["one.vel"], "mappings": "AAAA;AAAA"}
    mapping = SourceFile(
        "src/generated.ts",
        "",
        source_map=json.dumps(
            {
                "version": 3,
                "sections": [
                    {"offset": {"line": 0, "column": 0}, "map": inner},
                    {
                        "offset": {"line": 0, "column": 5},
                        "map": {**inner, "sources": ["two.vel"], "mappings": "AAAA"},
                    },
                ],
            }
        ),
    )
    result = remap_diagnostics((diag(1, 1), diag(1, 6), diag(2, 1)), (mapping,))
    assert result[0].file == "src/one.vel"
    assert result[1].file == "src/two.vel"
    assert result[2] == diag(2, 1)


@pytest.mark.parametrize("mappings", ["g", "!", "AA", "AAAAAA", "ACAA", "DAAA", "AAAA,", "g" * 20])
def test_invalid_vlq_rejected(mappings: str) -> None:
    with pytest.raises(AdapterMappingError):
        remap_diagnostics((diag(1, 1),), (source(mappings),))


def test_real_compiler_error_maps_component_position(tsgo_binary: Path, tmp_path: Path) -> None:
    class Adapter:
        name = "mapped-component"

        def get_sources(self, root: str) -> list[SourceFile]:
            return [
                SourceFile(
                    "src/Button.vel.ts",
                    '// generated header\nexport const count: number = "wrong";',
                    origin_path="src/Button.vel",
                    source_map=json.dumps(
                        {
                            "version": 3,
                            "sources": ["Button.vel"],
                            "mappings": ";" + vlq(13, 0, 8, 6),
                        }
                    ),
                )
            ]

    result = check_project(tmp_path, adapter=Adapter())
    assert len(result.errors) == 1
    error = result.errors[0]
    assert (error.code, error.file, error.line, error.column) == (2322, "src/Button.vel", 9, 7)


def test_utf16_columns_with_emoji(tsgo_binary: Path, tmp_path: Path) -> None:
    text = 'export const emoji = "😀"; export const wrong: number = "x";'
    column = len(text[: text.index("wrong")].encode("utf-16-le")) // 2

    class Adapter:
        name = "unicode-component"

        def get_sources(self, root: str) -> list[SourceFile]:
            return [
                SourceFile(
                    "src/generated.ts",
                    text,
                    source_map=json.dumps(
                        {
                            "version": 3,
                            "sources": ["original.vel"],
                            "mappings": vlq(column, 0, 6, 10),
                        }
                    ),
                )
            ]

    result = check_project(tmp_path, adapter=Adapter())
    error = result.errors[0]
    assert (error.file, error.line, error.column) == ("src/original.vel", 7, 11)
