"""Fixtures for compatibility tests."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def running_platform() -> dict[str, str]:
    """Describe the running platform in a portable way."""
    return {
        "system": sys.platform,
        "machine": platform.machine().lower(),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "implementation": sys.implementation.name,
    }


@pytest.fixture(scope="session")
def tsgo_full_version(tsgo_binary: Path) -> str:
    """The full output of `tsgo --version`, trimmed."""
    result = subprocess.run(
        [str(tsgo_binary), "--version"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        shell=False,
    )
    return (result.stdout + result.stderr).strip()


@pytest.fixture
def sample_bad_file(tmp_path: Path) -> Path:
    f = tmp_path / "bad.ts"
    f.write_text('export const age: number = "twenty";\n', encoding="utf-8")
    return f


@pytest.fixture
def sample_good_file(tmp_path: Path) -> Path:
    f = tmp_path / "good.ts"
    f.write_text("export const age: number = 20;\n", encoding="utf-8")
    return f


@pytest.fixture
def manifest_platforms(manifest_path: Path) -> dict:
    """The `platforms` mapping from the manifest, or skip if absent."""
    if not manifest_path.exists():
        pytest.skip(f"no manifest at {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    platforms = data.get("platforms")
    if not platforms:
        pytest.skip("manifest has no platform entries")
    return platforms