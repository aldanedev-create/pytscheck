"""Tests that malformed or hostile JSON cannot exhaust resources."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pytscheck.adapters.errors import AdapterMappingError
from pytscheck.adapters.source_maps import remap_diagnostics
from pytscheck.exceptions import ConfigurationError
from pytscheck.models import Diagnostic, SourceFile


def _diag(file: str = "a.ts") -> Diagnostic:
    return Diagnostic(file=file, line=1, column=1, code=1, category="error", message="m")


def test_deeply_nested_json_in_source_map() -> None:
    """A source map with massive nesting must be rejected or handled."""
    bomb = "[" * 100_000 + "]" * 100_000
    src = SourceFile(
        path="a.ts",
        text="",
        origin_path="a.vel",
        source_map=bomb,
        kind="generated",
    )
    # Either a mapping error or a JSON error, but not a crash loop.
    with pytest.raises((AdapterMappingError, RecursionError, ValueError)):
        remap_diagnostics((_diag("a.ts"),), (src,))


def test_huge_json_string_in_source_map() -> None:
    payload = '{"version": 3, "mappings": "' + "A" * 10_000_000 + '"}'
    src = SourceFile(
        path="a.ts",
        text="",
        origin_path="a.vel",
        source_map=payload,
        kind="generated",
    )
    try:
        out = remap_diagnostics((_diag("a.ts"),), (src,))
    except AdapterMappingError:
        return
    assert out[0].file == "a.vel"


def test_non_object_json_in_source_map() -> None:
    for payload in ['"string"', "42", "true", "null", "[]"]:
        src = SourceFile(
            path="a.ts",
            text="",
            origin_path="a.vel",
            source_map=payload,
            kind="generated",
        )
        with pytest.raises(AdapterMappingError):
            remap_diagnostics((_diag("a.ts"),), (src,))


def test_tsconfig_with_json_bomb(tmp_path: Path) -> None:
    from pytscheck.config import load_tsconfig

    bomb = "[" * 50_000 + "]" * 50_000
    p = tmp_path / "tsconfig.json"
    p.write_text(bomb, encoding="utf-8")
    with pytest.raises((ConfigurationError, RecursionError)):
        load_tsconfig(p)


def test_tsconfig_with_giant_string(tmp_path: Path) -> None:
    from pytscheck.config import load_tsconfig

    payload = '{"a": "' + "x" * 10_000_000 + '"}'
    p = tmp_path / "tsconfig.json"
    p.write_text(payload, encoding="utf-8")
    data = load_tsconfig(p)
    assert isinstance(data, dict)


def test_tsconfig_with_huge_array(tmp_path: Path) -> None:
    from pytscheck.config import load_tsconfig

    payload = '{"a": [' + ",".join("1" for _ in range(1_000_000)) + "]}"
    p = tmp_path / "tsconfig.json"
    p.write_text(payload, encoding="utf-8")
    # Either parse succeeds or fails, but no crash
    try:
        data = load_tsconfig(p)
    except ConfigurationError:
        return
    assert isinstance(data, dict)


def test_tsconfig_with_duplicate_keys(tmp_path: Path) -> None:
    from pytscheck.config import load_tsconfig

    p = tmp_path / "tsconfig.json"
    p.write_text('{"a": 1, "a": 2}', encoding="utf-8")
    data = load_tsconfig(p)
    # Standard json takes the last value
    assert data["a"] == 2


def test_tsconfig_with_invalid_utf8_bytes(tmp_path: Path) -> None:
    from pytscheck.config import load_tsconfig

    p = tmp_path / "tsconfig.json"
    p.write_bytes(b'{"a": "\xff\xfe"}')
    with pytest.raises(ConfigurationError):
        load_tsconfig(p)


def test_source_map_with_extra_large_array_field() -> None:
    payload = json.dumps({"version": 3, "mappings": "", "sources": ["x"] * 1_000_000})
    src = SourceFile(
        path="a.ts",
        text="",
        origin_path="a.vel",
        source_map=payload,
        kind="generated",
    )
    # Should parse without crashing (memory limits apply at OS level)
    out = remap_diagnostics((_diag("a.ts"),), (src,))
    assert out[0].file == "a.vel"


def test_json_with_nested_key_objects() -> None:
    """`mappings` must be a value, not nested structures."""
    payload = json.dumps({"version": 3, "mappings": {"deep": {"deeper": {"deepest": 1}}}})
    src = SourceFile(
        path="a.ts",
        text="",
        origin_path="a.vel",
        source_map=payload,
        kind="generated",
    )
    # Only the presence of "mappings" is required by the parser;
    # a non-string value may or may not be rejected, but no crash.
    try:
        out = remap_diagnostics((_diag("a.ts"),), (src,))
    except AdapterMappingError:
        return
    assert out[0].file == "a.vel"


def test_json_with_control_characters() -> None:
    payload = '{"version": 3, "mappings": "\x00\x01\x02"}'
    src = SourceFile(
        path="a.ts",
        text="",
        origin_path="a.vel",
        source_map=payload,
        kind="generated",
    )
    try:
        out = remap_diagnostics((_diag("a.ts"),), (src,))
    except AdapterMappingError:
        return
    assert out[0].file == "a.vel"


def test_source_map_not_a_string() -> None:
    """A non-string source_map field is only possible by bypassing types.
    The dataclass accepts it; the parser must fail cleanly."""
    src = SourceFile(
        path="a.ts",
        text="",
        origin_path="a.vel",
        source_map=12345,  # type: ignore[arg-type]
        kind="generated",
    )
    with pytest.raises((AdapterMappingError, TypeError, AttributeError)):
        remap_diagnostics((_diag("a.ts"),), (src,))
