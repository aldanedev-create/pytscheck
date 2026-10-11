"""Integration tests for repeated / incremental checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import check_project


def test_repeated_project_checks_consistent(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "main.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    results = [check_project(tmp_path) for _ in range(3)]
    assert all(r.success for r in results)


def test_fixing_error_makes_check_pass(tsgo_binary, tmp_path: Path) -> None:
    f = tmp_path / "main.ts"
    f.write_text('export const x: number = "s";\n', encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    assert not check_project(tmp_path).success

    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    assert check_project(tmp_path).success


def test_adding_error_changes_result(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "main.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    assert check_project(tmp_path).success

    (tmp_path / "extra.ts").write_text('export const y: number = "s";\n', encoding="utf-8")
    assert not check_project(tmp_path).success


def test_no_caching_staleness(tsgo_binary, tmp_path: Path) -> None:
    """Editing a file must be observed on the next check."""
    f = tmp_path / "main.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    assert check_project(tmp_path).success

    for i in range(5):
        f.write_text(f'export const x: number = "iter{i}";\n', encoding="utf-8")
        assert not check_project(tmp_path).success

    f.write_text("export const x: number = 42;\n", encoding="utf-8")
    assert check_project(tmp_path).success


def test_no_leftover_files_from_incremental_checks(
    tsgo_binary, tmp_path: Path
) -> None:
    (tmp_path / "main.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    before = set(p.name for p in tmp_path.iterdir())
    for _ in range(3):
        check_project(tmp_path)
    after = set(p.name for p in tmp_path.iterdir())
    assert before == after