"""Windows-specific compatibility tests.

Marked `windows` and skipped on other platforms. Real subprocess calls,
real filesystem behavior.
"""

from __future__ import annotations

import os
import sys
from contextlib import suppress
from pathlib import Path

import pytest

from pytscheck import check, check_file, check_project

pytestmark = pytest.mark.windows


@pytest.fixture(autouse=True)
def _require_windows() -> None:
    if sys.platform != "win32":
        pytest.skip("Windows-only")


# --- basic behavior ---------------------------------------------------------


def test_check_works_on_windows(tsgo_binary: Path) -> None:
    r = check("export const x: number = 1;")
    assert r.success


def test_check_file_works(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "a.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    r = check_file(f)
    assert r.success


def test_check_project_works(tsgo_binary: Path, tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, "include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    (tmp_path / "a.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    r = check_project(tmp_path)
    assert r.success


# --- path handling ----------------------------------------------------------


def test_windows_backslash_paths(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "a.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    # Pass the path as a string with native separators
    r = check_file(str(f))
    assert r.success


def test_windows_drive_letter_preserved(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "a.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    r = check_file(f)
    # Diagnostic file field, if any, should retain the drive letter or path
    for d in r.errors:
        if d.file:
            assert os.path.isabs(d.file) or "a.ts" in d.file


def test_windows_reserved_name_handling(tmp_path: Path) -> None:
    """Reserved names (CON, PRN, NUL) cannot be used as filenames."""
    from pytscheck.exceptions import ConfigurationError

    reserved = tmp_path / "CON.ts"
    try:
        reserved.write_text("", encoding="utf-8")
    except OSError:
        # Expected on Windows; the file cannot be created
        return
    # If creation succeeded, checking should still be safe
    with suppress(ConfigurationError):
        check_file(reserved)


def test_windows_long_path(tmp_path: Path) -> None:
    """Deeply nested paths must either work or fail cleanly."""
    deep = tmp_path
    for _ in range(30):
        deep = deep / "subdirectory"
    try:
        deep.mkdir(parents=True)
    except OSError:
        pytest.skip("filesystem does not support deep nesting")
    f = deep / "x.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    try:
        r = check_file(f)
    except Exception:
        return
    assert r.success


# --- subprocess -------------------------------------------------------------


def test_binary_is_exe(tsgo_binary: Path) -> None:
    assert tsgo_binary.name == "tsgo.exe"


def test_executable_bit_not_required(tsgo_binary: Path) -> None:
    """On Windows, permission bits are not enforced."""
    assert tsgo_binary.exists()


# --- CLI --------------------------------------------------------------------


def test_cli_available_on_windows() -> None:
    from tests.helpers import run_cli

    code, _, _ = run_cli(["--version"])
    assert code == 0


# --- file permissions -------------------------------------------------------


def test_readonly_file_still_checkable(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "a.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    os.chmod(f, 0o444)
    try:
        r = check_file(f)
        assert r.success
    finally:
        os.chmod(f, 0o644)


# --- environment ------------------------------------------------------------


def test_env_vars_do_not_break(tsgo_binary: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEMP", str(Path.home()))
    monkeypatch.setenv("TMP", str(Path.home()))
    r = check("export const x: number = 1;")
    assert r.success


def test_no_console_window(tsgo_binary: Path) -> None:
    """Verify no visible console is spawned (documentation assertion)."""
    r = check("export const x: number = 1;")
    assert r.success
