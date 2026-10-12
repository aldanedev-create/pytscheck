"""macOS-specific compatibility tests."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

import pytest

from pytscheck import check, check_file, check_project

pytestmark = pytest.mark.macos


@pytest.fixture(autouse=True)
def _require_macos() -> None:
    if sys.platform != "darwin":
        pytest.skip("macOS-only")


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


# --- binary format ----------------------------------------------------------


def test_binary_is_macho(tsgo_binary: Path) -> None:
    """macOS binaries are Mach-O, not ELF."""
    with tsgo_binary.open("rb") as fh:
        magic = fh.read(4)
    # Mach-O magic numbers: 0xFEEDFACE, 0xFEEDFACF, 0xCAFEBABE, 0xCAFEBABF
    valid = {
        b"\xce\xfa\xed\xfe",  # 32-bit little-endian
        b"\xcf\xfa\xed\xfe",  # 64-bit little-endian
        b"\xfe\xed\xfa\xce",  # 32-bit big-endian
        b"\xfe\xed\xfa\xcf",  # 64-bit big-endian
    }
    assert magic in valid, f"unexpected Mach-O magic: {magic!r}"


def test_binary_arch_matches_host(tsgo_binary: Path) -> None:
    result = subprocess.run(
        ["file", str(tsgo_binary)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        shell=False,
    )
    if result.returncode != 0:
        pytest.skip("`file` not available")
    info = result.stdout.lower()
    machine = platform.machine().lower()
    if machine == "arm64":
        assert "arm64" in info or "aarch64" in info
    elif machine in {"x86_64", "amd64"}:
        assert "x86_64" in info or "x86-64" in info


# --- gatekeeper / quarantine ------------------------------------------------


def test_binary_is_executable(tsgo_binary: Path) -> None:
    assert os.access(tsgo_binary, os.X_OK)


def test_binary_not_quarantined(tsgo_binary: Path) -> None:
    """Quarantine attribute blocks execution; wheels must not set it."""
    result = subprocess.run(
        ["xattr", "-p", "com.apple.quarantine", str(tsgo_binary)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        shell=False,
    )
    # Exit code 1 means "attribute not present" -- which is what we want.
    # If xattr is missing, skip.
    if "No such file" in result.stderr or result.returncode not in {0, 1}:
        pytest.skip("xattr not available")
    assert result.returncode != 0, f"quarantine attribute set on {tsgo_binary}: {result.stdout}"


# --- case insensitivity (HFS+/APFS default) --------------------------------


def test_case_behavior_documented(tmp_path: Path) -> None:
    """Default macOS volumes are case-insensitive; skip if not."""
    a = tmp_path / "a.ts"
    a.write_text("", encoding="utf-8")
    A = tmp_path / "A.ts"
    if not A.exists():
        pytest.skip("filesystem is case-sensitive (unusual for macOS)")
    # Case-insensitive: both paths resolve to the same file
    assert a.resolve() == A.resolve() or a.samefile(A)


# --- environment ------------------------------------------------------------


def test_check_without_home(tsgo_binary: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", "/nonexistent-home")
    assert check("export const x: number = 1;").success


def test_check_in_temp_dir(tsgo_binary: Path) -> None:
    """macOS temp dirs under /var/folders must work."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "a.ts"
        f.write_text("export const x: number = 1;\n", encoding="utf-8")
        assert check_file(f).success


# --- symlinks ---------------------------------------------------------------


def test_symlink_supported(tsgo_binary: Path, tmp_path: Path) -> None:
    real = tmp_path / "real.ts"
    real.write_text("export const x: number = 1;\n", encoding="utf-8")
    link = tmp_path / "link.ts"
    link.symlink_to(real)
    assert check_file(link).success
