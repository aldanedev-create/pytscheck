"""Tests that the CLI produces the same outcome as the Python API."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import check, check_file, check_project
from tests.helpers import parse_cli_json, run_cli


def test_string_parity(tsgo_binary) -> None:
    src = 'const age: number = "twenty";'
    api = check(src)
    code, out, _ = run_cli(["string", src, "--json"])
    cli = parse_cli_json(out)
    assert cli["success"] == api.success
    assert [d["code"] for d in cli["diagnostics"]] == [d.code for d in api.diagnostics]


def test_valid_string_parity(tsgo_binary) -> None:
    src = "export const x: number = 1;"
    api = check(src)
    _, out, _ = run_cli(["string", src, "--json"])
    cli = parse_cli_json(out)
    assert cli["success"] == api.success
    assert cli["diagnostics"] == []


def test_file_parity(tsgo_binary, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('export const age: number = "twenty";\n', encoding="utf-8")
    api = check_file(f)
    _, out, _ = run_cli(["file", str(f), "--json"])
    cli = parse_cli_json(out)
    assert cli["success"] == api.success
    assert [d["code"] for d in cli["diagnostics"]] == [d.code for d in api.diagnostics]


def test_project_parity(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "main.ts").write_text(
        'export const x: number = "bad";\n', encoding="utf-8"
    )
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    api = check_project(tmp_path)
    _, out, _ = run_cli(["project", str(tmp_path), "--json"])
    cli = parse_cli_json(out)
    assert cli["success"] == api.success


def test_exit_code_matches_success(tsgo_binary) -> None:
    code, _, _ = run_cli(["string", "export const x: number = 1;"])
    assert code == 0


def test_exit_code_matches_error(tsgo_binary) -> None:
    code, _, _ = run_cli(["string", 'const x: number = "s";'])
    assert code == 1


def test_compiler_version_parity(tsgo_binary) -> None:
    api = check("export const x: number = 1;")
    _, out, _ = run_cli(["string", "export const x: number = 1;", "--json"])
    cli = parse_cli_json(out)
    assert cli["compiler_version"] == api.compiler_version


def test_diagnostic_fields_parity(tsgo_binary) -> None:
    src = 'const age: number = "twenty";'
    api = check(src)
    _, out, _ = run_cli(["string", src, "--json"])
    cli = parse_cli_json(out)
    for api_d, cli_d in zip(api.diagnostics, cli["diagnostics"], strict=False):
        assert api_d.line == cli_d["line"]
        assert api_d.column == cli_d["column"]
        assert api_d.code == cli_d["code"]
        assert api_d.category == cli_d["category"]
        assert api_d.message == cli_d["message"]