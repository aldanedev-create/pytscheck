"""Integration tests for .d.ts declaration file handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import check_project
from tests.assertions import assert_valid_result


def test_declaration_file_provides_globals(
    tsgo_binary, project_declaration_files: Path
) -> None:
    r = check_project(project_declaration_files)
    assert r.success, [d.message for d in r.errors]


def test_declaration_file_missing_symbol(
    tsgo_binary, tmp_path: Path
) -> None:
    (tmp_path / "types.d.ts").write_text(
        "declare function greet(name: string): string;\n", encoding="utf-8"
    )
    (tmp_path / "main.ts").write_text(
        "export const s: string = notDeclared();\n", encoding="utf-8"
    )
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    r = check_project(tmp_path)
    assert not r.success


def test_declaration_file_types_checked(
    tsgo_binary, tmp_path: Path
) -> None:
    (tmp_path / "types.d.ts").write_text(
        "declare function greet(name: string): string;\n", encoding="utf-8"
    )
    (tmp_path / "main.ts").write_text(
        "export const s: string = greet(42);\n",  # wrong argument type
        encoding="utf-8",
    )
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    r = check_project(tmp_path)
    assert not r.success


def test_module_declaration(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "types.d.ts").write_text(
        'declare module "vendor" {\n'
        "  export function parse(s: string): number;\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "main.ts").write_text(
        'import { parse } from "vendor";\n'
        "export const n: number = parse('42');\n",
        encoding="utf-8",
    )
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]


def test_declaration_files_are_not_emitted(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "types.d.ts").write_text(
        "declare const x: number;\n", encoding="utf-8"
    )
    (tmp_path / "main.ts").write_text("export const y = 1;\n", encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    check_project(tmp_path)
    # The .d.ts file should not be rewritten, and no new .js emitted
    assert not (tmp_path / "main.js").exists()
    original = (tmp_path / "types.d.ts").read_text(encoding="utf-8")
    assert "declare const x: number;" in original