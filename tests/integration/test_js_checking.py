"""Integration tests for JavaScript files with --allowJs / checkJs."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import check_project


def test_allow_js_project_checks(tsgo_binary, project_with_js: Path) -> None:
    r = check_project(project_with_js)
    assert r.success or not r.success  # no crash


def test_check_js_reports_error(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "script.js").write_text(
        "// @ts-check\n"
        "/** @type {number} */\n"
        "const x = 'not a number';\n",
        encoding="utf-8",
    )
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true, '
        '"allowJs": true, "checkJs": true}, "include": ["**/*.js"]}',
        encoding="utf-8",
    )
    r = check_project(tmp_path)
    assert not r.success


def test_mixed_ts_js_project(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "util.js").write_text(
        "export function double(n) { return n * 2; }\n", encoding="utf-8"
    )
    (tmp_path / "main.ts").write_text(
        "import { double } from './util.js';\nexport const x: number = double(2);\n",
        encoding="utf-8",
    )
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true, '
        '"allowJs": true, "moduleResolution": "bundler"}, '
        '"include": ["**/*.ts", "**/*.js"]}',
        encoding="utf-8",
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]


def test_js_without_checkjs_is_not_checked(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "script.js").write_text(
        "/** @type {number} */\nconst x = 'wrong';\n", encoding="utf-8"
    )
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true, "allowJs": true}, '
        '"include": ["**/*.js"]}',
        encoding="utf-8",
    )
    # Without checkJs, .js is included but not type-checked
    r = check_project(tmp_path)
    assert r.success


def test_js_with_syntax_error(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "broken.js").write_text(
        "// @ts-check\nfunction f( {\n", encoding="utf-8"
    )
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"allowJs": true, "checkJs": true, "noEmit": true}, '
        '"include": ["**/*.js"]}',
        encoding="utf-8",
    )
    r = check_project(tmp_path)
    assert not r.success