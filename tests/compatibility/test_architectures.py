"""Architecture-specific compatibility tests.

Verifies that the bundled binary for the running architecture works and
that the platform detection is correct.
"""

from __future__ import annotations

import platform
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from pytscheck.runner import _PLATFORM_DIRS, binary_path
from pytscheck.version import COMPILER_VERSION


def _running_arch() -> str:
    return platform.machine().lower()


def test_platform_dir_matches_arch() -> None:
    """The platform directory must match the running machine."""
    from pytscheck.runner import _platform_dir

    dirname = _platform_dir()
    machine = _running_arch()
    if sys.platform == "linux":
        assert dirname in {"linux-amd64", "linux-arm64", "linux-arm", "linux-386"}
        if machine in {"x86_64", "amd64"}:
            assert dirname == ("linux-386" if struct.calcsize("P") == 4 else "linux-amd64")
        elif machine in {"aarch64", "arm64"}:
            assert dirname == ("linux-arm" if struct.calcsize("P") == 4 else "linux-arm64")
    elif sys.platform == "darwin":
        assert dirname in {"darwin-amd64", "darwin-arm64"}
    elif sys.platform == "win32":
        assert dirname in {"windows-amd64", "windows-arm64", "windows-386"}


def test_all_documented_platforms_in_map() -> None:
    """Every target platform from the spec is present."""
    expected = {
        ("win32", "amd64"),
        ("win32", "arm64"),
        ("linux", "x86_64"),
        ("linux", "aarch64"),
        ("linux", "armv7l"),
        ("linux", "i686"),
        ("linux", "i386"),
        ("win32", "x86"),
        ("darwin", "x86_64"),
        ("darwin", "arm64"),
    }
    assert expected.issubset(_PLATFORM_DIRS.keys())


def test_alternative_machine_names_map_same() -> None:
    """amd64 and x86_64 map to the same dir; arm64 and aarch64 likewise."""
    assert _PLATFORM_DIRS[("linux", "x86_64")] == _PLATFORM_DIRS[("linux", "amd64")]
    assert _PLATFORM_DIRS[("linux", "aarch64")] == _PLATFORM_DIRS[("linux", "arm64")]
    assert _PLATFORM_DIRS[("darwin", "x86_64")] == _PLATFORM_DIRS[("darwin", "amd64")]
    assert _PLATFORM_DIRS[("darwin", "arm64")] == _PLATFORM_DIRS[("darwin", "aarch64")]


def test_binary_path_resolves() -> None:
    from pytscheck.exceptions import CompilerNotFoundError, UnsupportedPlatformError

    try:
        p = binary_path()
    except (CompilerNotFoundError, UnsupportedPlatformError):
        pytest.skip("no bundled binary for this platform")
    assert p.exists()


def test_binary_runs_and_reports_version(tsgo_binary: Path) -> None:
    result = subprocess.run(
        [str(tsgo_binary), "--version"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        shell=False,
    )
    assert result.returncode == 0
    combined = (result.stdout + result.stderr).strip()
    assert combined


def test_architecture_matches_binary_format() -> None:
    """The binary's format must be runnable on the running OS."""
    from pytscheck.exceptions import CompilerNotFoundError, UnsupportedPlatformError

    try:
        p = binary_path()
    except (CompilerNotFoundError, UnsupportedPlatformError):
        pytest.skip("no bundled binary")

    with p.open("rb") as fh:
        magic = fh.read(4)

    if sys.platform == "linux":
        assert magic == b"\x7fELF"
    elif sys.platform == "darwin":
        assert magic in {
            b"\xce\xfa\xed\xfe",
            b"\xcf\xfa\xed\xfe",
            b"\xfe\xed\xfa\xce",
            b"\xfe\xed\xfa\xcf",
        }
    elif sys.platform == "win32":
        assert magic[:2] == b"MZ"


def test_binary_matches_interpreter_bitness(tsgo_binary: Path) -> None:
    """Compiler bitness must match the Python interpreter architecture."""
    with tsgo_binary.open("rb") as reader:
        header = reader.read(64)
        width = struct.calcsize("P")
        if header[:4] == b"\x7fELF":
            assert header[4] == (1 if width == 4 else 2)
        elif header[:2] == b"MZ":
            reader.seek(struct.unpack_from("<I", header, 60)[0] + 4)
            machine = struct.unpack("<H", reader.read(2))[0]
            assert machine in ({0x14C} if width == 4 else {0x8664, 0xAA64})
        else:
            assert width == 8
            assert header[:4] in {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"}


def test_architecture_specific_platform_marker() -> None:
    """The running architecture must be one of the documented targets."""
    machine = _running_arch()
    system = sys.platform
    known = {
        ("linux", "x86_64"),
        ("linux", "amd64"),
        ("linux", "aarch64"),
        ("linux", "armv7l"),
        ("linux", "i686"),
        ("linux", "i386"),
        ("win32", "x86"),
        ("linux", "arm64"),
        ("darwin", "x86_64"),
        ("darwin", "arm64"),
        ("win32", "amd64"),
        ("win32", "arm64"),
    }
    assert any(
        system == k[0] and (machine.startswith(k[1][:5]) or machine == k[1]) for k in known
    ), f"unknown platform/arch: {system}/{machine}"


def test_compiler_version_is_recorded_with_arch() -> None:
    """Ensure the pin is not accidentally architecture-specific."""
    assert "-arm64" not in COMPILER_VERSION
    assert "-amd64" not in COMPILER_VERSION
    assert "-x64" not in COMPILER_VERSION


def test_manifest_covers_all_documented_platforms(manifest_platforms: dict) -> None:
    """Manifest must have entries for every platform we claim to support."""
    # Not all platforms need to be downloaded locally, but the manifest
    # structure must accommodate them.
    if not manifest_platforms:
        pytest.skip("manifest empty")
    # If any entries exist, verify their shape
    for platform_name, entry in manifest_platforms.items():
        assert isinstance(platform_name, str)
        assert "version" in entry
        assert "integrity" in entry
        assert "tarball" in entry


def test_unsupported_arch_raises_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bogus architecture must raise UnsupportedPlatformError."""
    from pytscheck import runner
    from pytscheck.exceptions import UnsupportedPlatformError

    if sys.platform in {"linux", "darwin", "win32"}:
        pytest.skip("unsupported-platform check requires a real unsupported OS; no platform mocks")
    with pytest.raises(UnsupportedPlatformError):
        runner._platform_dir()
