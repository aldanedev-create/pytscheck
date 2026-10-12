"""Tests for the packaging metadata of pytscheck."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from tests.helpers import read_metadata_from_wheel


@pytest.fixture(scope="module")
def pyproject(repo_root: Path) -> dict:
    data = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    return data


def test_name_is_pytscheck(pyproject: dict) -> None:
    assert pyproject["project"]["name"] == "pytscheck"


def test_requires_python_is_311(pyproject: dict) -> None:
    assert pyproject["project"]["requires-python"] == ">=3.11"


def test_license_is_apache(pyproject: dict) -> None:
    license_field = pyproject["project"].get("license")
    if isinstance(license_field, dict):
        assert license_field.get("text") == "Apache-2.0"
    else:
        assert license_field == "Apache-2.0"


def test_version_is_dynamic_from_module(pyproject: dict) -> None:
    # Under hatchling, version comes from src/pytscheck/version.py
    hatch = pyproject.get("tool", {}).get("hatch", {})
    if "version" in hatch:
        assert hatch["version"]["path"] == "src/pytscheck/version.py"
    else:
        # Static version is acceptable
        assert "version" in pyproject["project"]


def test_classifiers_include_3_11_3_12_3_13(pyproject: dict) -> None:
    classifiers = pyproject["project"]["classifiers"]
    for v in ("3.11", "3.12", "3.13"):
        assert f"Programming Language :: Python :: {v}" in classifiers


def test_dependencies_are_empty(pyproject: dict) -> None:
    assert pyproject["project"].get("dependencies", []) == []


def test_entry_point_group_declared(pyproject: dict) -> None:
    entry_points = pyproject["project"].get("entry-points", {})
    assert "pytscheck.adapters" in entry_points


def test_console_script_declared(pyproject: dict) -> None:
    scripts = pyproject["project"].get("scripts", {})
    assert scripts.get("pytscheck") == "pytscheck.__main__:main"


def test_build_system_is_hatchling(pyproject: dict) -> None:
    build_system = pyproject["build-system"]
    assert "hatchling" in " ".join(build_system["requires"])
    assert build_system["build-backend"] == "hatchling.build"


def test_wheel_metadata_matches_pyproject(built_wheel: Path, pyproject: dict) -> None:
    metadata = read_metadata_from_wheel(built_wheel)
    assert f"Name: {pyproject['project']['name']}" in metadata
    assert f"Requires-Python: {pyproject['project']['requires-python']}" in metadata


def test_readme_is_markdown(pyproject: dict) -> None:
    readme = pyproject["project"]["readme"]
    assert readme.endswith(".md") or readme == "README.md"


def test_urls_are_https(pyproject: dict) -> None:
    urls = pyproject["project"].get("urls", {})
    for name, url in urls.items():
        assert url.startswith("https://"), f"{name} not https: {url}"
