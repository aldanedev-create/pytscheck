"""Tests for pytscheck.resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck.exceptions import ConfigurationError
from pytscheck.resolver import ResolvedProject, resolve_project


def test_resolve_empty_project(tmp_path: Path) -> None:
    rp = resolve_project(tmp_path)
    assert isinstance(rp, ResolvedProject)
    assert rp.root == tmp_path.resolve()
    assert rp.tsconfig is None
    assert rp.package_json is None
    assert rp.extends is None


def test_resolve_project_with_tsconfig(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text("{}")
    rp = resolve_project(tmp_path)
    assert rp.tsconfig == tmp_path / "tsconfig.json"
    assert rp.extends is None


def test_resolve_project_with_package_json(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name": "x"}')
    rp = resolve_project(tmp_path)
    assert rp.package_json == tmp_path / "package.json"


def test_resolve_project_with_both(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text("{}")
    (tmp_path / "package.json").write_text("{}")
    rp = resolve_project(tmp_path)
    assert rp.tsconfig is not None
    assert rp.package_json is not None


def test_resolve_project_extends_relative(tmp_path: Path) -> None:
    (tmp_path / "base.json").write_text("{}")
    (tmp_path / "tsconfig.json").write_text('{"extends": "./base.json"}')
    rp = resolve_project(tmp_path)
    assert rp.extends == "./base.json"


def test_resolve_project_extends_escape_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text('{"extends": "../../etc/passwd"}')
    with pytest.raises(ConfigurationError, match="escapes"):
        resolve_project(tmp_path)


def test_resolve_project_root_is_resolved(tmp_path: Path) -> None:
    rp = resolve_project(tmp_path / ".")
    assert rp.root == tmp_path.resolve()


def test_resolve_project_extends_non_string_ignored(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text('{"extends": 42}')
    rp = resolve_project(tmp_path)
    assert rp.extends is None


def test_resolve_project_malformed_tsconfig_raises(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text("{ bad json")
    with pytest.raises(ConfigurationError):
        resolve_project(tmp_path)


def test_resolved_project_is_frozen(tmp_path: Path) -> None:
    import dataclasses

    rp = resolve_project(tmp_path)
    with pytest.raises(dataclasses.FrozenInstanceError):
        rp.root = Path("/")  # type: ignore[misc]


def test_resolve_project_ignores_tsconfig_directory(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").mkdir()
    rp = resolve_project(tmp_path)
    assert rp.tsconfig is None


def test_resolver_all_names_exist() -> None:
    from pytscheck import resolver

    for name in resolver.__all__:
        assert hasattr(resolver, name), f"missing: {name}"
