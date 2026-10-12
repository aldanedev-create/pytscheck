"""Tests for pytscheck.client.

The client delegates to the real checker. These tests call it against real
files. Tests that require the bundled binary skip if it is not present.
"""

from __future__ import annotations

from pathlib import Path

from pytscheck.client import Client
from pytscheck.models import Result
from tests.assertions import assert_valid_result


def test_client_check_against_valid_source(tsgo_binary: Path) -> None:
    r = Client().check("export const x: number = 1;")
    assert_valid_result(r)
    assert r.success, [d.message for d in r.errors]


def test_client_check_against_type_error(tsgo_binary: Path) -> None:
    r = Client().check('const age: number = "twenty";')
    assert_valid_result(r)
    assert not r.success
    assert any(d.code == 2322 for d in r.errors), [d.code for d in r.errors]


def test_client_check_file(tsgo_binary: Path, ts_file_valid: Path) -> None:
    r = Client().check_file(ts_file_valid)
    assert_valid_result(r)
    assert r.success


def test_client_check_file_with_error(tsgo_binary: Path, ts_file_type_error: Path) -> None:
    r = Client().check_file(ts_file_type_error)
    assert_valid_result(r)
    assert not r.success


def test_client_check_project(tsgo_binary: Path, project_type_error: Path) -> None:
    r = Client().check_project(project_type_error)
    assert_valid_result(r)
    assert not r.success


def test_client_returns_result_instance(tsgo_binary: Path) -> None:
    r = Client().check("const x = 1;")
    assert isinstance(r, Result)


def test_client_can_be_instantiated_without_arguments() -> None:
    c = Client()
    assert c is not None
    assert c.runner is None


def test_client_keep_raw_flag(tsgo_binary: Path) -> None:
    r = Client().check('const age: number = "twenty";', keep_raw=True)
    assert r.raw_output is not None
    assert "2322" in r.raw_output or "error" in r.raw_output.lower()


def test_client_custom_filename(tsgo_binary: Path) -> None:
    r = Client().check('const age: number = "twenty";', filename="custom.ts")
    assert not r.success
    assert any(d.file == "custom.ts" for d in r.errors)
