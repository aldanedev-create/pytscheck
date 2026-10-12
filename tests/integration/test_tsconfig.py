"""Integration tests for tsconfig.json handling."""

from __future__ import annotations

from pathlib import Path

from pytscheck import check_project
from tests.assertions import assert_valid_result


def test_strict_mode_enforced(tsgo_binary, tsconfig_strict: Path, tmp_path: Path) -> None:
    """Under strict, null/undefined checks apply."""
    (tmp_path / "main.ts").write_text(
        "export function f(x: string | null): number { return x.length; }\n",
        encoding="utf-8",
    )
    r = check_project(tmp_path)
    assert not r.success


def test_no_emit_enforced(tsgo_binary, tsconfig_no_emit_disabled: Path, tmp_path: Path) -> None:
    (tmp_path / "main.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    r = check_project(tmp_path)
    assert r.success
    assert not (tmp_path / "main.js").exists()


def test_paths_alias_resolved(tsgo_binary, tsconfig_paths_alias: Path, tmp_path: Path) -> None:
    (tmp_path / "src" / "consumer.ts").write_text(
        "import { double } from '@lib/math';\nexport const y: number = double(3);\n",
        encoding="utf-8",
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]


def test_broken_tsconfig_reports_error(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text("{ invalid json", encoding="utf-8")
    (tmp_path / "main.ts").write_text("export const x = 1;\n", encoding="utf-8")
    try:
        r = check_project(tmp_path)
    except Exception:
        return  # a configuration error is acceptable
    assert not r.success


def test_tsconfig_include_limits_files(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, "include": ["src/**/*.ts"]}',
        encoding="utf-8",
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    (tmp_path / "outside.ts").write_text('export const bad: number = "string";\n', encoding="utf-8")
    r = check_project(tmp_path)
    # The outside file should not be included
    assert r.success


def test_tsconfig_exclude(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"], "exclude": ["excluded/**/*"]}',
        encoding="utf-8",
    )
    (tmp_path / "main.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    (tmp_path / "excluded").mkdir()
    (tmp_path / "excluded" / "bad.ts").write_text(
        'export const bad: number = "string";\n', encoding="utf-8"
    )
    r = check_project(tmp_path)
    assert r.success


def test_tsconfig_extends(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "base.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}}', encoding="utf-8"
    )
    (tmp_path / "tsconfig.json").write_text(
        '{"extends": "./base.json", "include": ["**/*.ts"]}', encoding="utf-8"
    )
    (tmp_path / "main.ts").write_text(
        "export function f(x: string | null): number { return x.length; }",
        encoding="utf-8",
    )
    r = check_project(tmp_path)
    # Extends inherits strict, so this should fail
    assert not r.success


def test_tsconfig_with_allow_js(tsgo_binary, project_with_js: Path) -> None:
    r = check_project(project_with_js)
    assert_valid_result(r)


def test_tsconfig_target_es2022(tsgo_binary, tsconfig_strict: Path, tmp_path: Path) -> None:
    (tmp_path / "main.ts").write_text(
        "export const s: string = 'x'?.toString() ?? 'default';\n",
        encoding="utf-8",
    )
    r = check_project(tmp_path)
    assert r.success


def test_tsconfig_module_resolution_bundler(
    tsgo_binary, tsconfig_strict: Path, tmp_path: Path
) -> None:
    (tmp_path / "util.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    (tmp_path / "main.ts").write_text(
        "import { x } from './util';\nexport const y: number = x;\n",
        encoding="utf-8",
    )
    r = check_project(tmp_path)
    assert r.success
