"""Tests for pytscheck.project."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck.exceptions import ConfigurationError
from pytscheck.project import describe_project, iter_typescript_files


# --- iter_typescript_files --------------------------------------------------


def test_iter_empty_project(tmp_path: Path) -> None:
    assert iter_typescript_files(tmp_path) == ()


def test_iter_finds_ts_files(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text("")
    (tmp_path / "b.tsx").write_text("")
    (tmp_path / "c.mts").write_text("")
    (tmp_path / "d.cts").write_text("")
    files = iter_typescript_files(tmp_path)
    assert len(files) == 4
    assert {p.name for p in files} == {"a.ts", "b.tsx", "c.mts", "d.cts"}


def test_iter_ignores_non_typescript(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text("")
    (tmp_path / "b.js").write_text("")
    (tmp_path / "c.json").write_text("")
    (tmp_path / "d.txt").write_text("")
    assert len(iter_typescript_files(tmp_path)) == 1


def test_iter_skips_node_modules(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text("")
    nm = tmp_path / "node_modules" / "pkg"
    nm.mkdir(parents=True)
    (nm / "b.ts").write_text("")
    files = iter_typescript_files(tmp_path)
    assert len(files) == 1
    assert files[0].name == "a.ts"


def test_iter_recurses_subdirectories(tmp_path: Path) -> None:
    sub = tmp_path / "src" / "deep"
    sub.mkdir(parents=True)
    (sub / "a.ts").write_text("")
    files = iter_typescript_files(tmp_path)
    assert len(files) == 1
    assert files[0].name == "a.ts"


def test_iter_returns_sorted_tuple(tmp_path: Path) -> None:
    (tmp_path / "z.ts").write_text("")
    (tmp_path / "a.ts").write_text("")
    (tmp_path / "m.ts").write_text("")
    files = iter_typescript_files(tmp_path)
    assert isinstance(files, tuple)
    assert [p.name for p in files] == ["a.ts", "m.ts", "z.ts"]


def test_iter_respects_max_files(tmp_path: Path) -> None:
    for i in range(5):
        (tmp_path / f"f{i}.ts").write_text("")
    with pytest.raises(ConfigurationError, match="exceeds"):
        iter_typescript_files(tmp_path, max_files=3)


def test_iter_max_files_boundary(tmp_path: Path) -> None:
    for i in range(3):
        (tmp_path / f"f{i}.ts").write_text("")
    assert len(iter_typescript_files(tmp_path, max_files=3)) == 3


# --- describe_project ------------------------------------------------------


def test_describe_project_without_tsconfig(tmp_path: Path) -> None:
    info = describe_project(tmp_path)
    assert info["root"] == str(tmp_path)
    assert info["has_tsconfig"] is False
    assert info["tsconfig_path"] is None


def test_describe_project_with_tsconfig(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text("{}")
    info = describe_project(tmp_path)
    assert info["has_tsconfig"] is True
    assert info["tsconfig_path"] == str(tmp_path / "tsconfig.json")


def test_describe_project_returns_dict(tmp_path: Path) -> None:
    info = describe_project(tmp_path)
    assert isinstance(info, dict)
    assert set(info.keys()) == {"root", "has_tsconfig", "tsconfig_path"}


# --- module exports --------------------------------------------------------


def test_project_all_names_exist() -> None:
    from pytscheck import project

    for name in project.__all__:
        assert hasattr(project, name), f"missing: {name}"