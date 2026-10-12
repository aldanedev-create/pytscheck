"""Tests for pytscheck.config."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path

import pytest

from pytscheck.config import (
    CompilerOptions,
    find_tsconfig,
    load_tsconfig,
    validate_project_root,
)
from pytscheck.exceptions import ConfigurationError

# --- CompilerOptions -------------------------------------------------------


def test_compiler_options_defaults() -> None:
    o = CompilerOptions()
    assert o.strict is True
    assert o.no_emit is True
    assert o.skip_lib_check is False
    assert o.types == ()
    assert o.lib == ()
    assert o.target is None
    assert o.module is None
    assert o.module_resolution is None
    assert o.extra == {}


def test_compiler_options_is_frozen() -> None:
    import dataclasses

    o = CompilerOptions()
    with pytest.raises(dataclasses.FrozenInstanceError):
        o.strict = False  # type: ignore[misc]


# --- find_tsconfig ---------------------------------------------------------


def test_find_tsconfig_returns_path_when_present(tmp_path: Path) -> None:
    p = tmp_path / "tsconfig.json"
    p.write_text("{}")
    assert find_tsconfig(tmp_path) == p


def test_find_tsconfig_returns_none_when_absent(tmp_path: Path) -> None:
    assert find_tsconfig(tmp_path) is None


def test_find_tsconfig_ignores_directory(tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").mkdir()
    assert find_tsconfig(tmp_path) is None


def test_find_tsconfig_in_nested_project(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    p = tmp_path / "nested" / "tsconfig.json"
    p.write_text("{}")
    assert find_tsconfig(tmp_path / "nested") == p


# --- load_tsconfig ---------------------------------------------------------


def test_load_tsconfig_valid(tmp_path: Path) -> None:
    p = tmp_path / "tsconfig.json"
    p.write_text('{"compilerOptions": {"strict": true}}')
    data = load_tsconfig(p)
    assert data["compilerOptions"]["strict"] is True


def test_load_tsconfig_invalid_json(tmp_path: Path) -> None:
    p = tmp_path / "tsconfig.json"
    p.write_text("{ bad")
    with pytest.raises(ConfigurationError, match="invalid JSON"):
        load_tsconfig(p)


def test_load_tsconfig_not_object(tmp_path: Path) -> None:
    p = tmp_path / "tsconfig.json"
    p.write_text('"a string"')
    with pytest.raises(ConfigurationError, match="must be an object"):
        load_tsconfig(p)


def test_load_tsconfig_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="cannot read"):
        load_tsconfig(tmp_path / "missing.json")


def test_load_tsconfig_utf8_bom(tmp_path: Path) -> None:
    p = tmp_path / "tsconfig.json"
    p.write_bytes(b"\xef\xbb\xbf{}")
    # JSON with a BOM: our reader uses utf-8 (not utf-8-sig), so this should
    # either parse (if BOM stripped) or raise ConfigurationError.
    with suppress(ConfigurationError):
        load_tsconfig(p)


# --- validate_project_root -------------------------------------------------


def test_validate_project_root_ok(tmp_path: Path) -> None:
    assert validate_project_root(tmp_path) == tmp_path


def test_validate_project_root_missing(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        validate_project_root(tmp_path / "nope")


def test_validate_project_root_not_directory(tmp_path: Path) -> None:
    f = tmp_path / "file"
    f.write_text("")
    with pytest.raises(ConfigurationError, match="not a directory"):
        validate_project_root(f)


# --- module exports --------------------------------------------------------


def test_config_all_names_exist() -> None:
    from pytscheck import config

    for name in config.__all__:
        assert hasattr(config, name), f"missing: {name}"
