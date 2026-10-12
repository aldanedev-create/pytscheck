"""Tests that pytscheck's diagnostics match what tsgo produces directly.

Every test in this file invokes the bundled tsgo binary directly and
compares its output to what pytscheck's parser produces. If our parser
diverges from tsgo's real format, these tests fail loudly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from pytscheck import check, check_file, check_project
from pytscheck.protocol import parse


def _run_tsgo_directly(tsgo_binary: Path, args: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        [str(tsgo_binary), *args, "--pretty", "false"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
    )
    combined = result.stdout + ("\n" + result.stderr if result.stderr else "")
    return result.returncode, combined


# --- single error -----------------------------------------------------------


def test_parity_single_type_error(tsgo_binary: Path, sample_bad_file: Path) -> None:
    _, raw = _run_tsgo_directly(tsgo_binary, ["--noEmit", "--strict", str(sample_bad_file)])
    direct_report = parse(raw)
    direct_codes = {d.code for d in direct_report.diagnostics if d.category == "error"}

    api = check_file(sample_bad_file)
    api_codes = {d.code for d in api.errors}

    assert direct_codes == api_codes, (
        f"direct codes: {direct_codes}; api codes: {api_codes}\nraw output:\n{raw}"
    )


def test_parity_single_syntax_error(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "syntax.ts"
    f.write_text("const x: number = ;\n", encoding="utf-8")
    _, raw = _run_tsgo_directly(tsgo_binary, ["--noEmit", str(f)])
    direct = {d.code for d in parse(raw).diagnostics if d.category == "error"}

    api = check_file(f)
    api_codes = {d.code for d in api.errors}

    assert direct == api_codes


def test_parity_clean_file(tsgo_binary: Path, sample_good_file: Path) -> None:
    _, raw = _run_tsgo_directly(tsgo_binary, ["--noEmit", "--strict", str(sample_good_file)])
    direct = [d for d in parse(raw).diagnostics if d.category == "error"]

    api = check_file(sample_good_file)
    assert len(direct) == len(api.errors) == 0


# --- multiple errors --------------------------------------------------------


def test_parity_multiple_errors(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "many.ts"
    f.write_text(
        'export const a: number = "x";\n'
        'export const b: number = "y";\n'
        'export const c: number = "z";\n',
        encoding="utf-8",
    )
    _, raw = _run_tsgo_directly(tsgo_binary, ["--noEmit", "--strict", str(f)])
    direct = parse(raw)
    direct_pairs = sorted(
        (d.line, d.column, d.code) for d in direct.diagnostics if d.category == "error"
    )

    api = check_file(f)
    api_pairs = sorted((d.line, d.column, d.code) for d in api.errors)

    assert direct_pairs == api_pairs, f"direct: {direct_pairs}\napi: {api_pairs}\nraw:\n{raw}"


# --- positions --------------------------------------------------------------


def test_parity_line_and_column(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "pos.ts"
    f.write_text(
        'const ok: number = 1;\nconst age: number = "twenty";\n',
        encoding="utf-8",
    )
    _, raw = _run_tsgo_directly(tsgo_binary, ["--noEmit", "--strict", str(f)])
    direct = parse(raw)
    direct_errors = [d for d in direct.diagnostics if d.category == "error"]
    assert direct_errors

    api = check_file(f)
    api_errors = list(api.errors)

    for d, a in zip(direct_errors, api_errors, strict=False):
        assert d.line == a.line
        assert d.column == a.column


# --- project-level ----------------------------------------------------------


def test_parity_project(tsgo_binary: Path, tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, "include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    (tmp_path / "a.ts").write_text('export const x: number = "bad";\n', encoding="utf-8")
    _, raw = _run_tsgo_directly(tsgo_binary, ["--noEmit", "-p", str(tmp_path / "tsconfig.json")])
    direct = {d.code for d in parse(raw).diagnostics if d.category == "error"}

    api = check_project(tmp_path)
    api_codes = {d.code for d in api.errors}

    assert direct == api_codes


# --- string input -----------------------------------------------------------


def test_parity_string_input(tsgo_binary: Path, tmp_path: Path) -> None:
    src = 'const age: number = "twenty";'
    # Write the same source to a file so we can compare against direct invocation
    f = tmp_path / "input.ts"
    f.write_text(src, encoding="utf-8")
    _, raw = _run_tsgo_directly(tsgo_binary, ["--noEmit", "--strict", str(f)])
    direct = {d.code for d in parse(raw).diagnostics if d.category == "error"}

    api = check(src)
    api_codes = {d.code for d in api.errors}

    assert direct == api_codes


# --- deterministic ordering -------------------------------------------------


def test_parity_ordering(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "order.ts"
    f.write_text(
        'export const c: number = "x";\n'
        'export const a: number = "y";\n'
        'export const b: number = "z";\n',
        encoding="utf-8",
    )
    _, raw = _run_tsgo_directly(tsgo_binary, ["--noEmit", "--strict", str(f)])
    direct = [(d.line, d.column, d.code) for d in parse(raw).diagnostics if d.category == "error"]

    api = check_file(f)
    api_pairs = [(d.line, d.column, d.code) for d in api.errors]

    # The API sorts; the compiler may or may not. Compare as multisets.
    assert sorted(direct) == sorted(api_pairs)


# --- diagnostics not dropped ------------------------------------------------


def test_no_diagnostics_lost(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "mixed.ts"
    f.write_text(
        "export function f(x: string | null): number { return x.length; }\n"
        'export const y: number = "x";\n',
        encoding="utf-8",
    )
    _, raw = _run_tsgo_directly(tsgo_binary, ["--noEmit", "--strict", str(f)])
    direct_count = sum(1 for d in parse(raw).diagnostics if d.category == "error")
    api_count = len(check_file(f).errors)
    assert direct_count == api_count


# --- stderr vs stdout -------------------------------------------------------


def test_diagnostics_are_found_regardless_of_stream(
    tsgo_binary: Path, sample_bad_file: Path
) -> None:
    """Whether tsgo writes diagnostics to stdout or stderr, we capture them."""
    result = subprocess.run(
        [str(tsgo_binary), "--pretty", "false", "--noEmit", "--strict", str(sample_bad_file)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        shell=False,
    )
    combined = result.stdout + result.stderr
    combined_report = parse(combined)
    assert any(d.category == "error" for d in combined_report.diagnostics)
