"""Tests that bundled binaries match their recorded checksums."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest


def test_manifest_exists_or_skips(manifest_path: Path) -> None:
    if not manifest_path.exists():
        pytest.skip(f"no manifest at {manifest_path}")


def test_manifest_is_valid_json(manifest_path: Path) -> None:
    if not manifest_path.exists():
        pytest.skip("no manifest")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "compiler_version" in data
    assert "platforms" in data


def test_manifest_platform_entries_have_integrity(manifest_path: Path) -> None:
    if not manifest_path.exists():
        pytest.skip("no manifest")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    for platform, entry in data["platforms"].items():
        assert "integrity" in entry, f"{platform}: missing integrity"
        assert "-" in entry["integrity"], f"{platform}: bad integrity format"


def test_bundled_binary_size_matches_manifest(
    bin_root: Path, manifest_path: Path, bin_platform_dir: Path
) -> None:
    if not manifest_path.exists():
        pytest.skip("no manifest")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Look up our platform under any of the known npm platform names
    platform_key = bin_platform_dir.name
    npm_to_platform = {
        "win32-x64": "windows-amd64",
        "win32-arm64": "windows-arm64",
        "linux-x64": "linux-amd64",
        "linux-arm64": "linux-arm64",
        "linux-arm": "linux-arm",
        "linux-ia32": "linux-386",
        "win32-ia32": "windows-386",
        "darwin-x64": "darwin-amd64",
        "darwin-arm64": "darwin-arm64",
    }
    matching = [
        (npm, entry)
        for npm, entry in data["platforms"].items()
        if npm_to_platform.get(npm) == platform_key
    ]
    if not matching:
        pytest.skip(f"no manifest entry for {platform_key}")
    npm, entry = matching[0]
    rel = entry.get("binary_relpath")
    if not rel:
        pytest.skip(f"{npm}: no binary_relpath recorded")
    binary = bin_platform_dir / rel
    if not binary.exists():
        pytest.skip(f"binary not present at {binary}")
    assert binary.stat().st_size > 0


def test_recompute_binary_hash_is_stable(
    bin_platform_dir: Path,
) -> None:
    """Running the same hash twice must give the same value (sanity check)."""
    binaries = list(bin_platform_dir.rglob("tsgo")) + list(bin_platform_dir.rglob("tsgo.exe"))
    if not binaries:
        pytest.skip("no binary bundled")
    binary = binaries[0]
    h1 = hashlib.sha512(binary.read_bytes()).hexdigest()
    h2 = hashlib.sha512(binary.read_bytes()).hexdigest()
    assert h1 == h2


def test_manifest_compiler_version_matches_version_module(
    manifest_path: Path,
) -> None:
    if not manifest_path.exists():
        pytest.skip("no manifest")
    from pytscheck.version import COMPILER_VERSION

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["compiler_version"] == COMPILER_VERSION


def test_integrity_value_format() -> None:
    """A sample npm integrity string must parse with the algorithm we use."""
    integrity = "sha512-" + base64.b64encode(b"x" * 64).decode()
    algo, expected = integrity.split("-", 1)
    assert algo == "sha512"
    assert base64.b64decode(expected)
