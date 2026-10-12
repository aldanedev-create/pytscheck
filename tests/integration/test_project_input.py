"""Integration tests for checking whole projects."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import check_project
from tests.assertions import assert_has_error_code, assert_valid_result


def _write_project(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


def test_minimal_project(tsgo_binary, tsconfig_strict: Path, tmp_path: Path) -> None:
    (tmp_path / "main.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    r = check_project(tmp_path)
    assert_valid_result(r)
    assert r.success


def test_project_with_error(tsgo_binary, tsconfig_strict: Path, tmp_path: Path) -> None:
    (tmp_path / "main.ts").write_text('export const x: number = "s";\n', encoding="utf-8")
    r = check_project(tmp_path)
    assert not r.success
    assert_has_error_code(r, 2322)


def test_project_with_nested_directories(
    tsgo_binary, tsconfig_strict: Path, tmp_path: Path
) -> None:
    _write_project(
        tmp_path,
        {
            "src/a.ts": "export const a: number = 1;\n",
            "src/sub/b.ts": "export const b: number = 2;\n",
            "src/sub/deep/c.ts": "export const c: number = 3;\n",
        },
    )
    r = check_project(tmp_path)
    assert r.success


def test_project_with_many_files(tsgo_binary, tsconfig_strict: Path, tmp_path: Path) -> None:
    files = {f"f{i}.ts": f"export const x{i}: number = {i};\n" for i in range(20)}
    _write_project(tmp_path, files)
    r = check_project(tmp_path)
    assert r.success


def test_project_with_one_bad_file(tsgo_binary, tsconfig_strict: Path, tmp_path: Path) -> None:
    files = {f"ok{i}.ts": f"export const x{i}: number = {i};\n" for i in range(5)}
    files["bad.ts"] = 'export const age: number = "twenty";\n'
    _write_project(tmp_path, files)
    r = check_project(tmp_path)
    assert not r.success
    assert any("bad.ts" in (d.file or "") for d in r.errors)


def test_project_without_tsconfig(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "main.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    r = check_project(tmp_path)
    # Either success or a diagnostic about missing config; either way, no crash.
    assert_valid_result(r)


def test_project_diagnostics_carry_paths(
    tsgo_binary, tsconfig_strict: Path, tmp_path: Path
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "bad.ts").write_text('export const x: number = "s";\n', encoding="utf-8")
    r = check_project(tmp_path)
    assert r.errors
    for d in r.errors:
        assert d.file is not None


def test_project_check_does_not_emit(tsgo_binary, tsconfig_strict: Path, tmp_path: Path) -> None:
    (tmp_path / "main.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    check_project(tmp_path)
    assert not (tmp_path / "main.js").exists()
    assert not (tmp_path / "main.d.ts").exists()


def test_project_check_accepts_relative_path(
    tsgo_binary, tsconfig_strict: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "main.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    r = check_project(".")
    assert r.success


def test_project_check_missing_raises(tmp_path: Path) -> None:
    from pytscheck.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError, match="does not exist"):
        check_project(tmp_path / "missing")


def test_project_check_file_path_raises(tsgo_binary, tmp_path: Path) -> None:
    from pytscheck.exceptions import ConfigurationError

    f = tmp_path / "a.ts"
    f.write_text("", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="not a directory"):
        check_project(f)


def test_project_with_imports(tsgo_binary, tsconfig_strict: Path, tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        {
            "src/util.ts": "export function double(n: number): number { return n * 2; }\n",
            "src/main.ts": (
                "import { double } from './util';\nexport const x: number = double(2);\n"
            ),
        },
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]


def test_project_with_broken_import(tsgo_binary, tsconfig_strict: Path, tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        {
            "src/main.ts": "import { missing } from './nonexistent';\nexport const x = missing;\n",
        },
    )
    r = check_project(tmp_path)
    assert not r.success


def test_project_elapsed_seconds_positive(
    tsgo_binary, tsconfig_strict: Path, tmp_path: Path
) -> None:
    (tmp_path / "main.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    r = check_project(tmp_path)
    assert r.elapsed_seconds > 0.0
