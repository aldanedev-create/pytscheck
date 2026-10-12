"""Packaging safeguards for actual static Linux compilers and x86 provenance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from scripts.build_binaries import (
    PLATFORMS,
    SOURCE_COMMIT,
    SOURCE_GO_VERSION,
    SOURCE_TARGETS,
    verify_static_linux,
)
from scripts.hatch_build import TAGS


def test_linux_wheel_tags_cover_glibc_and_musl() -> None:
    from packaging.utils import parse_wheel_filename

    for target in ("linux-x64", "linux-arm64", "linux-arm", "linux-ia32"):
        _, _, _, tags = parse_wheel_filename(f"pytscheck-0.1.0-py3-none-{TAGS[target]}.whl")
        assert any(tag.platform.startswith("musllinux_1_2_") for tag in tags)
        assert any(tag.platform.startswith("manylinux_2_17_") for tag in tags)


def test_dynamic_python_cannot_be_shipped_as_a_musl_compiler() -> None:
    if sys.platform != "linux":
        pytest.skip("real Linux ELF test")
    from scripts.generate_manifest import _PLATFORM_DIRS

    from pytscheck.runner import _platform_dir

    target = next(key for key, value in _PLATFORM_DIRS.items() if value == _platform_dir())
    with pytest.raises(RuntimeError, match="fully static"):
        verify_static_linux(Path(sys.executable).resolve(), target)


def test_downloaded_linux_compilers_are_static_and_match_cpu(bin_root: Path) -> None:
    found = False
    for target, directory in PLATFORMS.items():
        binary = bin_root / directory / "lib/tsgo"
        if target.startswith("linux-") and binary.exists():
            verify_static_linux(binary, target)
            found = True
    if not found:
        pytest.skip("no downloaded Linux compiler")


def test_x86_manifest_records_exact_source_and_toolchain(manifest_path: Path) -> None:
    platforms = json.loads(manifest_path.read_text())["platforms"]
    for target in SOURCE_TARGETS:
        if target in platforms:
            assert platforms[target]["source_commit"] == SOURCE_COMMIT
            assert platforms[target]["go_version"] == SOURCE_GO_VERSION
            assert platforms[target]["libraries_platform"] in {"linux-x64", "win32-x64"}
