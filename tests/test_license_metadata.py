"""Tests for license metadata and bundled third-party notices."""

from __future__ import annotations

from pathlib import Path

from tests.helpers import list_wheel_members, read_license_from_wheel


def test_repo_has_license_file(repo_root: Path) -> None:
    assert (repo_root / "LICENSE").exists()


def test_repo_has_notice_file(repo_root: Path) -> None:
    assert (repo_root / "NOTICE.txt").exists()


def test_license_contains_apache_header(repo_root: Path) -> None:
    text = (repo_root / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in text
    assert "Version 2.0" in text


def test_notice_mentions_bundled_compiler(repo_root: Path) -> None:
    text = (repo_root / "NOTICE.txt").read_text(encoding="utf-8")
    assert "typescript" in text.lower() or "tsgo" in text.lower()


def test_notice_mentions_apache(repo_root: Path) -> None:
    text = (repo_root / "NOTICE.txt").read_text(encoding="utf-8")
    assert "Apache" in text


def test_wheel_contains_license(built_wheel: Path) -> None:
    license_bytes = read_license_from_wheel(built_wheel)
    if license_bytes is None:
        # Some wheel layouts put LICENSE under .dist-info/licenses/
        members = list_wheel_members(built_wheel)
        assert any("LICENSE" in m for m in members)
        return
    assert b"Apache" in license_bytes


def test_wheel_contains_metadata_license_field(built_wheel: Path) -> None:
    from tests.helpers import read_metadata_from_wheel

    metadata = read_metadata_from_wheel(built_wheel)
    # PEP 639 style: License-Expression: Apache-2.0
    # Older style: License: Apache-2.0
    assert "Apache" in metadata


def test_bundled_license_if_binary_present(bin_root: Path) -> None:
    """If a platform binary is bundled, its LICENSE must be too."""
    for platform_dir in bin_root.glob("*-*"):
        if not platform_dir.is_dir():
            continue
        binaries = list(platform_dir.rglob("tsgo")) + list(platform_dir.rglob("tsgo.exe"))
        if not binaries:
            continue
        license_candidates = list(platform_dir.rglob("LICENSE")) + list(
            platform_dir.rglob("LICENSE.txt")
        )
        assert license_candidates, f"no LICENSE bundled in {platform_dir}"


def test_bundled_notice_if_binary_present(bin_root: Path) -> None:
    for platform_dir in bin_root.glob("*-*"):
        if not platform_dir.is_dir():
            continue
        binaries = list(platform_dir.rglob("tsgo")) + list(platform_dir.rglob("tsgo.exe"))
        if not binaries:
            continue
        notice = list(platform_dir.rglob("NOTICE.txt")) + list(platform_dir.rglob("NOTICE"))
        assert notice, f"no NOTICE bundled in {platform_dir}"


def test_pyproject_declares_license(repo_root: Path) -> None:
    import tomllib

    data = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    license_field = data["project"].get("license")
    if isinstance(license_field, dict):
        assert license_field.get("text") == "Apache-2.0"
    else:
        assert license_field == "Apache-2.0"
