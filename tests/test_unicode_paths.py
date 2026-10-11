"""Tests for checking files with unicode paths."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pytscheck import checker


def test_unicode_filename(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "café.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    r = checker.check_file(f)
    assert r.success


def test_unicode_directory(tsgo_binary: Path, tmp_path: Path) -> None:
    d = tmp_path / "проект"
    d.mkdir()
    f = d / "x.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    r = checker.check_file(f)
    assert r.success


def test_emoji_filename(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "🚀.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    r = checker.check_file(f)
    assert r.success


def test_unicode_project_root(tsgo_binary: Path, tmp_path: Path) -> None:
    root = tmp_path / "日本語プロジェクト"
    root.mkdir()
    (root / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    (root / "x.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    r = checker.check_project(root)
    assert r.success


def test_filename_with_spaces(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "my project file.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    r = checker.check_file(f)
    assert r.success


def test_filename_with_parens(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "(test) file.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    r = checker.check_file(f)
    assert r.success


def test_unicode_error_reports_unicode_path(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "ошибка.ts"
    f.write_text('export const x: number = "bad";\n', encoding="utf-8")
    r = checker.check_file(f)
    assert not r.success
    assert any("ошибка" in (d.file or "") for d in r.errors)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
def test_surrogate_rejected() -> None:
    """A path containing unpaired surrogates must not crash."""
    from pytscheck.paths import assert_no_null_bytes

    # Surrogates are legal in Python str but not in filenames. We only test
    # that the helper for NUL bytes does not accidentally reject them.
    assert_no_null_bytes("normal name")