"""Fixtures shared by integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tsconfig_strict(tmp_path: Path) -> Path:
    """A minimal strict tsconfig.json in tmp_path."""
    p = tmp_path / "tsconfig.json"
    p.write_text(
        "{\n"
        '  "compilerOptions": {\n'
        '    "strict": true,\n'
        '    "noEmit": true,\n'
        '    "target": "es2022",\n'
        '    "module": "esnext",\n'
        '    "moduleResolution": "bundler",\n'
        '    "skipLibCheck": true\n'
        "  },\n"
        '  "include": ["**/*.ts"]\n'
        "}\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def tsconfig_paths_alias(tmp_path: Path) -> Path:
    """tsconfig with a path alias mapping."""
    (tmp_path / "src" / "lib").mkdir(parents=True)
    (tmp_path / "src" / "lib" / "math.ts").write_text(
        "export function double(n: number): number { return n * 2; }\n",
        encoding="utf-8",
    )
    p = tmp_path / "tsconfig.json"
    p.write_text(
        "{\n"
        '  "compilerOptions": {\n'
        '    "strict": true,\n'
        '    "noEmit": true,\n'
        '    "baseUrl": ".",\n'
        '    "paths": { "@lib/*": ["src/lib/*"] }\n'
        "  },\n"
        '  "include": ["**/*.ts"]\n'
        "}\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def tsconfig_no_emit_disabled(tmp_path: Path) -> Path:
    """A tsconfig that does not set noEmit; pytscheck must still set it."""
    p = tmp_path / "tsconfig.json"
    p.write_text(
        '{"compilerOptions": {"strict": true}, "include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    return p


@pytest.fixture
def project_declaration_files(tmp_path: Path) -> Path:
    """A project with a hand-written .d.ts file."""
    (tmp_path / "types.d.ts").write_text(
        'declare function greet(name: string): string;\n'
        'declare const version: string;\n',
        encoding="utf-8",
    )
    (tmp_path / "main.ts").write_text(
        'export const s: string = greet(version);\n',
        encoding="utf-8",
    )
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def project_with_js(tmp_path: Path) -> Path:
    """A project mixing .ts and .js files."""
    (tmp_path / "util.js").write_text(
        "// @ts-check\n"
        "exports.double = function double(n) { return n * 2; };\n",
        encoding="utf-8",
    )
    (tmp_path / "main.ts").write_text(
        "export const x: number = 1;\n",
        encoding="utf-8",
    )
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true, "allowJs": true}, '
        '"include": ["**/*.ts", "**/*.js"]}',
        encoding="utf-8",
    )
    return tmp_path