"""Tests that the JSON schema of pytscheck output is stable across releases."""

from __future__ import annotations

from pathlib import Path

from tests.helpers import parse_cli_json, run_cli

# Schema version. If the JSON shape changes in a breaking way, this constant
# must be bumped and a migration path documented.

SCHEMA_FIELDS_TOP = {
    "success",
    "compiler_version",
    "elapsed_seconds",
    "diagnostics",
}

SCHEMA_FIELDS_DIAG = {
    "file",
    "origin_file",
    "line",
    "column",
    "end_line",
    "end_column",
    "code",
    "category",
    "message",
}


def test_top_level_schema(tsgo_binary: Path) -> None:
    _, out, _ = run_cli(["string", 'const age: number = "twenty";', "--json"])
    payload = parse_cli_json(out)
    assert set(payload.keys()) == SCHEMA_FIELDS_TOP


def test_diagnostic_schema(tsgo_binary: Path) -> None:
    _, out, _ = run_cli(["string", 'const age: number = "twenty";', "--json"])
    payload = parse_cli_json(out)
    assert payload["diagnostics"]
    assert set(payload["diagnostics"][0].keys()) == SCHEMA_FIELDS_DIAG


def test_category_values(tsgo_binary: Path) -> None:
    _, out, _ = run_cli(["string", 'const age: number = "twenty";', "--json"])
    payload = parse_cli_json(out)
    for d in payload["diagnostics"]:
        assert d["category"] in {"error", "warning", "suggestion", "message"}


def test_file_can_be_null_for_global(tsgo_binary: Path, tmp_path: Path) -> None:
    # A project with a broken config may produce a global diagnostic
    (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {}}', encoding="utf-8")
    # No .ts files -> tsgo produces TS18003 (no inputs)
    _, out, _ = run_cli(["project", str(tmp_path), "--json"])
    payload = parse_cli_json(out)
    for d in payload["diagnostics"]:
        assert d["file"] is None or isinstance(d["file"], str)


def test_code_is_integer(tsgo_binary: Path) -> None:
    _, out, _ = run_cli(["string", 'const age: number = "twenty";', "--json"])
    payload = parse_cli_json(out)
    for d in payload["diagnostics"]:
        assert isinstance(d["code"], int)
        assert d["code"] > 0


def test_compiler_version_is_populated(tsgo_binary: Path) -> None:
    _, out, _ = run_cli(["string", "export const x: number = 1;", "--json"])
    payload = parse_cli_json(out)
    assert payload["compiler_version"]
    assert isinstance(payload["compiler_version"], str)
