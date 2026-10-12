"""Linux-specific compatibility tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pytscheck import check, check_file, check_project

pytestmark = pytest.mark.linux


@pytest.fixture(autouse=True)
def _require_linux() -> None:
    if sys.platform != "linux":
        pytest.skip("Linux-only")


def test_check_works(tsgo_binary: Path) -> None:
    assert check("export const x: number = 1;").success


def test_check_file_works(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "a.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    assert check_file(f).success


def test_check_project_works(tsgo_binary: Path, tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}, "include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    (tmp_path / "a.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    assert check_project(tmp_path).success


# --- binary permissions -----------------------------------------------------


def test_binary_has_executable_bit(tsgo_binary: Path) -> None:
    assert tsgo_binary.stat().st_mode & 0o111


def test_binary_can_be_executed_directly(tsgo_binary: Path) -> None:
    import subprocess

    result = subprocess.run(
        [str(tsgo_binary), "--version"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        shell=False,
    )
    assert result.returncode == 0


# --- symlinks ---------------------------------------------------------------


def test_symlink_supported(tsgo_binary: Path, tmp_path: Path) -> None:
    real = tmp_path / "real.ts"
    real.write_text("export const x: number = 1;\n", encoding="utf-8")
    link = tmp_path / "link.ts"
    try:
        link.symlink_to(real)
    except OSError:
        pytest.skip("symlinks not supported on this filesystem")
    assert check_file(link).success


def test_binary_through_symlink(tmp_path: Path) -> None:
    """Symlinked binary paths should work if the target exists."""
    from pytscheck.runner import binary_path

    try:
        original = binary_path()
    except Exception:
        pytest.skip("no bundled binary")
    link = tmp_path / "tsgo-link"
    try:
        link.symlink_to(original)
    except OSError:
        pytest.skip("symlinks not supported")
    assert link.exists()


# --- case sensitivity -------------------------------------------------------


def test_case_sensitive_paths(tmp_path: Path, tsgo_binary: Path) -> None:
    """Linux filesystems are case-sensitive."""
    a = tmp_path / "a.ts"
    a.write_text("export const A: number = 1;\n", encoding="utf-8")
    A = tmp_path / "A.ts"
    if A.exists():
        pytest.skip("filesystem is case-insensitive")
    A.write_text("export const A2: number = 2;\n", encoding="utf-8")
    assert a != A
    assert check_file(a).success
    assert check_file(A).success


# --- subprocess -------------------------------------------------------------


def test_shebang_not_required(tsgo_binary: Path) -> None:
    """The bundled binary is a native executable, not a script."""
    with tsgo_binary.open("rb") as fh:
        magic = fh.read(4)
    # ELF magic for Linux
    assert magic == b"\x7fELF", f"unexpected magic: {magic!r}"


def test_binary_architecture_matches_kernel(tsgo_binary: Path) -> None:
    import platform
    import subprocess

    result = subprocess.run(
        ["file", str(tsgo_binary)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        shell=False,
    )
    if result.returncode != 0:
        pytest.skip("`file` command not available")
    machine = platform.machine().lower()
    info = result.stdout.lower()
    if machine in {"x86_64", "amd64"}:
        assert "x86-64" in info or "x86_64" in info
    elif machine in {"aarch64", "arm64"}:
        assert "aarch64" in info or "arm" in info


# --- environment ------------------------------------------------------------


def test_no_display_required(tsgo_binary: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Running without a DISPLAY must work."""
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    assert check("export const x: number = 1;").success


def test_no_home_required(tsgo_binary: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Running without HOME should still work if temp is writable."""
    monkeypatch.setenv("HOME", "/nonexistent-home")
    r = check("export const x: number = 1;")
    assert r.success
