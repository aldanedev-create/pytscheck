"""Tests for JSON output stability (CLI --json)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.helpers import parse_cli_json, run_cli


def test_json_is_valid(tsgo_binary: Path) -> None:
    code, out, _ = run_cli(["string", 'const age: number = "twenty";', "--json"])
    payload = parse_cli_json(out)
    assert isinstance(payload, dict)


def test_json_has_required_fields(tsgo_binary: Path) -> None:
    code, out, _ = run_cli(["string", 'const age: number = "twenty";', "--json"])
    payload = parse_cli_json(out)
    for field in (
        "success",
        "compiler_version",
        "elapsed_seconds",
        "diagnostics",
    ):
        assert field in payload


def test_json_success_flag(tsgo_binary: Path) -> None:
    _, out, _ = run_cli(["string", "export const x: number = 1;", "--json"])
    payload = parse_cli_json(out)
    assert payload["success"] is True


def test_json_success_false_with_error(tsgo_binary: Path) -> None:
    _, out, _ = run_cli(["string", 'const age: number = "twenty";', "--json"])
    payload = parse_cli_json(out)
    assert payload["success"] is False


def test_json_diagnostics_are_list(tsgo_binary: Path) -> None:
    _, out, _ = run_cli(["string", 'const age: number = "twenty";', "--json"])
    payload = parse_cli_json(out)
    assert isinstance(payload["diagnostics"], list)


def test_json_diagnostic_has_all_fields(tsgo_binary: Path) -> None:
    _, out, _ = run_cli(["string", 'const age: number = "twenty";', "--json"])
    payload = parse_cli_json(out)
    assert payload["diagnostics"], "expected at least one diagnostic"
    d = payload["diagnostics"][0]
    for field in (
        "file",
        "origin_file",
        "line",
        "column",
        "end_line",
        "end_column",
        "code",
        "category",
        "message",
    ):
        assert field in d, f"missing field: {field}"


def test_json_types_are_correct(tsgo_binary: Path) -> None:
    _, out, _ = run_cli(["string", 'const age: number = "twenty";', "--json"])
    payload = parse_cli_json(out)
    assert isinstance(payload["compiler_version"], str)
    assert isinstance(payload["elapsed_seconds"], (int, float))
    for d in payload["diagnostics"]:
        assert isinstance(d["line"], int)
        assert isinstance(d["column"], int)
        assert isinstance(d["code"], int)
        assert isinstance(d["category"], str)
        assert isinstance(d["message"], str)


def test_json_round_trips(tsgo_binary: Path) -> None:
    _, out, _ = run_cli(["string", 'const age: number = "twenty";', "--json"])
    first = parse_cli_json(out)
    second = json.loads(json.dumps(first))
    assert second == first


def test_json_file_check(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('export const age: number = "twenty";\n', encoding="utf-8")
    _, out, _ = run_cli(["file", str(f), "--json"])
    payload = parse_cli_json(out)
    assert payload["success"] is False
    assert any(d["code"] == 2322 for d in payload["diagnostics"])


def test_json_project_check(tsgo_binary: Path, tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    (tmp_path / "a.ts").write_text(
        'export const age: number = "twenty";\n', encoding="utf-8"
    )
    _, out, _ = run_cli(["project", str(tmp_path), "--json"])
    payload = parse_cli_json(out)
    assert payload["success"] is False


def test_json_no_diagnostics_is_empty_list(tsgo_binary: Path) -> None:
    _, out, _ = run_cli(["string", "export const x: number = 1;", "--json"])
    payload = parse_cli_json(out)
    assert payload["diagnostics"] == []


def test_json_is_utf8(tsgo_binary: Path) -> None:
    _, out, _ = run_cli(
        ["string", 'export const s: string = "héllo";', "--json"]
    )
    payload = parse_cli_json(out)
    assert isinstance(payload, dict)