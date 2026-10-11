"""Tests for checking very large TypeScript files."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import checker
from tests.assertions import assert_valid_result


def _make_big_file(path: Path, n_decls: int) -> Path:
    lines = ["// big file\n"]
    for i in range(n_decls):
        lines.append(f"export const x{i}: number = {i};\n")
    path.write_text("".join(lines), encoding="utf-8")
    return path


def test_large_valid_file(tsgo_binary: Path, tmp_path: Path) -> None:
    f = _make_big_file(tmp_path / "big.ts", 5_000)
    assert f.stat().st_size > 50_000
    r = checker.check_file(f)
    assert_valid_result(r)
    assert r.success


def test_large_file_with_one_error(tsgo_binary: Path, tmp_path: Path) -> None:
    lines = ["// big file with error\n"]
    for i in range(2_000):
        lines.append(f"export const x{i}: number = {i};\n")
    lines.append('export const bad: number = "string";\n')
    f = tmp_path / "big_err.ts"
    f.write_text("".join(lines), encoding="utf-8")
    r = checker.check_file(f)
    assert not r.success
    assert any(d.code == 2322 for d in r.errors)


def test_large_file_exceeds_source_limit(tsgo_binary: Path, tmp_path: Path) -> None:
    """A file larger than DEFAULT_MAX_SOURCE_BYTES must be rejected cleanly."""
    from pytscheck.defaults import DEFAULT_MAX_SOURCE_BYTES

    f = tmp_path / "huge.ts"
    # Write DEFAULT_MAX_SOURCE_BYTES + a bit
    target = DEFAULT_MAX_SOURCE_BYTES + 1024
    chunk = b"// padding\n"
    with f.open("wb") as fh:
        written = 0
        while written < target:
            fh.write(chunk)
            written += len(chunk)

    with pytest.raises(Exception):
        checker.check_file(f)


def test_large_file_reports_elapsed_time(tsgo_binary: Path, tmp_path: Path) -> None:
    f = _make_big_file(tmp_path / "big.ts", 3_000)
    r = checker.check_file(f)
    assert r.elapsed_seconds > 0.0


def test_large_file_with_many_errors(tsgo_binary: Path, tmp_path: Path) -> None:
    lines = [f'export const bad{i}: number = "s";\n' for i in range(500)]
    f = tmp_path / "many_err.ts"
    f.write_text("".join(lines), encoding="utf-8")
    r = checker.check_file(f)
    assert not r.success
    assert len(r.errors) >= 100