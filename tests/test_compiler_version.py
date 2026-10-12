"""Tests that the pinned compiler version is consistent everywhere.

Version lives in three places that must agree:

1. `src/pytscheck/version.py::COMPILER_VERSION`
2. `src/pytscheck/bin/manifest.json::compiler_version`
3. `scripts/build_binaries.py::VERSION`

If they drift, wheels and packages become unverifiable.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pytscheck.version import COMPILER_VERSION

# --- version.py -------------------------------------------------------------


def test_compiler_version_is_pinned_not_floating() -> None:
    assert COMPILER_VERSION
    assert COMPILER_VERSION.lower() not in {"latest", "*", "any", ""}


def test_compiler_version_looks_like_semver_prefix() -> None:
    assert re.match(r"^\d+\.\d+\.\d+", COMPILER_VERSION)


def test_compiler_version_matches_manifest(manifest_path: Path) -> None:
    if not manifest_path.exists():
        pytest.skip(f"no manifest at {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["compiler_version"] == COMPILER_VERSION


def test_compiler_version_matches_build_script(repo_root: Path) -> None:
    script = repo_root / "scripts" / "build_binaries.py"
    if not script.exists():
        pytest.skip("build_binaries.py not present")
    source = script.read_text(encoding="utf-8")
    # Find the VERSION constant
    match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', source, re.M)
    if match is None:
        pytest.skip("no VERSION constant in build_binaries.py")
    assert match.group(1) == COMPILER_VERSION


def test_compiler_version_is_not_vague_float() -> None:
    # A pinned version must have at least major.minor.patch
    parts = COMPILER_VERSION.split(".")
    assert len(parts) >= 3


def test_compiler_version_can_have_prerelease_suffix() -> None:
    """Prerelease suffixes are allowed but must be separated by a valid char."""
    # Legal: "7.0.0-dev.20260707.2", "7.0.0-rc.1", "7.0.0"
    # Illegal: "7.0.0dev" (no separator)
    assert re.match(r"^\d+\.\d+\.\d+(-[A-Za-z0-9.-]+)?$", COMPILER_VERSION)


# --- runner-reported version ------------------------------------------------


def test_tsgo_reports_a_version(tsgo_binary: Path, tsgo_version: str) -> None:
    assert tsgo_version


def test_tsgo_version_contains_a_number(tsgo_version: str) -> None:
    assert re.search(r"\d+\.\d+", tsgo_version), tsgo_version


def test_tsgo_version_is_consistent(tsgo_binary: Path) -> None:
    import subprocess

    r1 = subprocess.run(
        [str(tsgo_binary), "--version"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        shell=False,
    )
    r2 = subprocess.run(
        [str(tsgo_binary), "--version"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        shell=False,
    )
    assert r1.stdout == r2.stdout
    assert r1.returncode == r2.returncode


# --- Result metadata --------------------------------------------------------


def test_result_carries_compiler_version(tsgo_binary: Path) -> None:
    from pytscheck import checker

    r = checker.check_source("export const x: number = 1;")
    assert r.compiler_version


def test_result_compiler_version_matches_pin(tsgo_binary: Path) -> None:
    from pytscheck import checker

    r = checker.check_source("export const x: number = 1;")
    assert r.compiler_version == COMPILER_VERSION


def test_cli_json_reports_compiler_version(tsgo_binary: Path) -> None:
    from tests.helpers import parse_cli_json, run_cli

    _, out, _ = run_cli(["string", "export const x: number = 1;", "--json"])
    payload = parse_cli_json(out)
    assert payload["compiler_version"] == COMPILER_VERSION


# --- manifest consistency ---------------------------------------------------


def test_manifest_has_platforms_dict(manifest_path: Path) -> None:
    if not manifest_path.exists():
        pytest.skip("no manifest")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(data["platforms"], dict)


def test_manifest_platform_entries_have_expected_keys(manifest_path: Path) -> None:
    if not manifest_path.exists():
        pytest.skip("no manifest")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {"npm_platform", "version", "integrity", "tarball", "binary_relpath"}
    for platform, entry in data["platforms"].items():
        for key in required:
            assert key in entry, f"{platform}: missing {key}"


def test_manifest_platform_versions_match_top_level(manifest_path: Path) -> None:
    if not manifest_path.exists():
        pytest.skip("no manifest")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    for platform, entry in data["platforms"].items():
        assert entry["version"] == data["compiler_version"], platform
