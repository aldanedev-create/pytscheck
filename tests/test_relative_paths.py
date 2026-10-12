"""Tests for relative path handling across the API."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import checker
from pytscheck.paths import normalize


def test_normalize_relative_under_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert normalize("sub/file.ts") == (tmp_path / "sub" / "file.ts").resolve()


def test_check_file_with_relative_path(
    tsgo_binary: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "a.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    r = checker.check_file(Path("a.ts"))
    assert r.success


def test_check_file_with_dot_relative_path(
    tsgo_binary: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    r = checker.check_file(Path("./a.ts"))
    assert r.success


def test_check_file_with_parent_relative(
    tsgo_binary: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "a.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    monkeypatch.chdir(sub)
    r = checker.check_file(Path("../a.ts"))
    assert r.success


def test_check_project_with_relative_root(
    tsgo_binary: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, "include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    (tmp_path / "a.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    r = checker.check_project(Path("."))
    assert r.success


def test_check_file_missing_relative_reports_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pytscheck.exceptions import ConfigurationError

    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigurationError, match="does not exist"):
        checker.check_file(Path("nonexistent.ts"))


def test_check_file_accepts_string_path(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "a.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    r = checker.check_file(str(f))
    assert r.success


def test_check_project_dot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pytscheck.config import validate_project_root

    monkeypatch.chdir(tmp_path)
    assert validate_project_root(Path(".")) == tmp_path


def test_check_project_dotdot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from pytscheck.config import validate_project_root

    sub = tmp_path / "sub"
    sub.mkdir()
    monkeypatch.chdir(sub)
    assert validate_project_root(Path("..")) == tmp_path
