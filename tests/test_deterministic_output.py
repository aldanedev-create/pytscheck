"""Tests that identical inputs produce identical outputs."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import checker
from pytscheck.protocol import parse
from pytscheck.runner import run


def test_same_source_same_diagnostics(tsgo_binary: Path) -> None:
    src = 'const age: number = "twenty";'
    results = [checker.check_source(src) for _ in range(3)]
    first = results[0]
    for r in results[1:]:
        assert r.success == first.success
        assert r.diagnostics == first.diagnostics


def test_same_file_same_diagnostics(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('export const age: number = "twenty";\n', encoding="utf-8")
    results = [checker.check_file(f) for _ in range(3)]
    assert all(r.diagnostics == results[0].diagnostics for r in results)


def test_diagnostic_order_is_stable(tsgo_binary: Path, tmp_path: Path) -> None:
    lines = [f'export const bad_{i}: number = "s";\n' for i in range(5)]
    f = tmp_path / "many.ts"
    f.write_text("".join(lines), encoding="utf-8")
    first = checker.check_file(f)
    for _ in range(3):
        r = checker.check_file(f)
        assert [d.code for d in r.errors] == [d.code for d in first.errors]
        assert [(d.line, d.column) for d in r.errors] == [
            (d.line, d.column) for d in first.errors
        ]


def test_runner_output_is_byte_identical(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('export const age: number = "twenty";\n', encoding="utf-8")
    r1 = run(["--noEmit", "--strict", str(f)])
    r2 = run(["--noEmit", "--strict", str(f)])
    # stdout and stderr must be identical run-to-run for the same inputs
    assert r1.stdout == r2.stdout
    assert r1.stderr == r2.stderr


def test_protocol_parse_is_pure(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bad.ts"
    f.write_text('export const age: number = "twenty";\n', encoding="utf-8")
    r = run(["--noEmit", "--strict", str(f)])
    combined = r.stdout + "\n" + r.stderr
    a = parse(combined)
    b = parse(combined)
    assert a.diagnostics == b.diagnostics


def test_project_order_of_files_is_stable(tsgo_binary: Path, tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    for i in range(5):
        (tmp_path / f"f{i}.ts").write_text(
            f'export const x{i}: number = "bad";\n', encoding="utf-8"
        )

    r1 = checker.check_project(tmp_path)
    r2 = checker.check_project(tmp_path)
    assert [(d.file, d.line, d.code) for d in r1.errors] == [
        (d.file, d.line, d.code) for d in r2.errors
    ]


def test_no_random_ordering_from_hashing(tsgo_binary: Path, tmp_path: Path) -> None:
    """Diagnostic ordering must not depend on Python hash randomization."""
    import subprocess
    import sys

    code = (
        "from pytscheck import checker\n"
        "r = checker.check_source('export const a: number = \"x\"; "
        "export const b: number = \"y\";')\n"
        "print([(d.line, d.code) for d in r.errors])\n"
    )
    r1 = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
        env={"PYTHONHASHSEED": "0", **__import__("os").environ},
    )
    r2 = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
        env={"PYTHONHASHSEED": "12345", **__import__("os").environ},
    )
    assert r1.returncode == 0, r1.stderr
    assert r2.returncode == 0, r2.stderr
    assert r1.stdout == r2.stdout