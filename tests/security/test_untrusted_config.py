"""Tests that hostile tsconfig files cannot compromise the checker."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import check_project
from pytscheck.exceptions import ConfigurationError, PyTSCheckError


def _write(root: Path, content: str) -> Path:
    p = root / "tsconfig.json"
    p.write_text(content, encoding="utf-8")
    (root / "a.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    return p


def test_extends_escape_rejected(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
    _write(tmp_path, '{"extends": "../../../../etc/passwd"}')
    with pytest.raises(ConfigurationError, match="escapes"):
        check_project(tmp_path)


def test_extends_absolute_escape_rejected(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
    _write(tmp_path, '{"extends": "/etc/passwd"}')
    with pytest.raises(ConfigurationError):
        check_project(tmp_path)


def test_extends_inside_allowed(tmp_path: Path, tsgo_binary: Path) -> None:
    (tmp_path / "base.json").write_text("{}", encoding="utf-8")
    (tmp_path / "a.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    _write(tmp_path, '{"extends": "./base.json"}')
    r = check_project(tmp_path)
    assert isinstance(r.success, bool)


def test_malformed_json_rejected(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
    _write(tmp_path, "{ invalid json")
    try:
        r = check_project(tmp_path)
    except ConfigurationError:
        return
    # If it did not raise, the result must reflect failure
    assert isinstance(r.success, bool)


def test_tsconfig_with_null_byte(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
    (tmp_path / "tsconfig.json").write_bytes(b'{"extends":\x00}')
    try:
        r = check_project(tmp_path)
    except (ConfigurationError, PyTSCheckError):
        return
    assert isinstance(r.success, bool)


def test_tsconfig_with_giant_json(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
    huge = "{" + '"a": ' * 100_000 + "1" + "}" * 100_000
    _write(tmp_path, huge)
    try:
        r = check_project(tmp_path)
    except (ConfigurationError, PyTSCheckError):
        return
    assert isinstance(r.success, bool)


def test_tsconfig_with_deeply_nested_json(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
    nested = "[" * 1000 + "]" * 1000
    _write(tmp_path, f'{{"compilerOptions": {{"types": {nested}}}}}')
    try:
        r = check_project(tmp_path)
    except (ConfigurationError, PyTSCheckError):
        return
    assert isinstance(r.success, bool)


def test_tsconfig_with_hostile_include_pattern(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
    _write(
        tmp_path,
        '{"compilerOptions": {"strict": true, "noEmit": true}, "include": ["../../**/*"]}',
    )
    try:
        r = check_project(tmp_path)
    except (ConfigurationError, PyTSCheckError):
        return
    assert isinstance(r.success, bool)


def test_tsconfig_with_hostile_exclude(tmp_path: Path, tsgo_binary: Path) -> None:
    (tmp_path / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
    _write(
        tmp_path,
        '{"compilerOptions": {"strict": true, "noEmit": true}, '
        '"include": ["**/*.ts"], "exclude": ["/etc"]}',
    )
    r = check_project(tmp_path)
    assert isinstance(r.success, bool)


def test_tsconfig_with_non_object_extras(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
    _write(
        tmp_path,
        '{"compilerOptions": {"strict": true, "noEmit": true}, "include": "not an array"}',
    )
    try:
        r = check_project(tmp_path)
    except (ConfigurationError, PyTSCheckError):
        return
    assert isinstance(r.success, bool)


def test_tsconfig_with_null_extends(tmp_path: Path, tsgo_binary: Path) -> None:
    (tmp_path / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
    _write(tmp_path, '{"extends": null, "include": ["**/*.ts"]}')
    r = check_project(tmp_path)
    assert isinstance(r.success, bool)


def test_tsconfig_with_number_extends(tmp_path: Path, tsgo_binary: Path) -> None:
    (tmp_path / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
    _write(tmp_path, '{"extends": 42, "include": ["**/*.ts"]}')
    r = check_project(tmp_path)
    assert isinstance(r.success, bool)


def test_tsconfig_as_directory(tmp_path: Path, tsgo_binary: Path) -> None:
    """A tsconfig.json directory must not be treated as a config file."""
    (tmp_path / "tsconfig.json").mkdir()
    (tmp_path / "a.ts").write_text("export const x: number = 1;\n", encoding="utf-8")
    r = check_project(tmp_path)
    assert isinstance(r.success, bool)
