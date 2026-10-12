"""Tests for pytscheck.defaults."""

from __future__ import annotations

from pytscheck import defaults


def test_limits_are_positive() -> None:
    assert defaults.DEFAULT_TIMEOUT_SECONDS > 0
    assert defaults.DEFAULT_MAX_STDOUT_BYTES > 0
    assert defaults.DEFAULT_MAX_STDERR_BYTES > 0
    assert defaults.DEFAULT_MAX_SOURCE_BYTES > 0
    assert defaults.DEFAULT_MAX_FILES_PER_PROJECT > 0


def test_output_limits_are_reasonable() -> None:
    assert defaults.DEFAULT_MAX_STDOUT_BYTES >= 1_048_576
    assert defaults.DEFAULT_MAX_STDERR_BYTES >= 1_048_576
    assert defaults.DEFAULT_MAX_STDOUT_BYTES >= defaults.DEFAULT_MAX_STDERR_BYTES


def test_typescript_extensions() -> None:
    assert ".ts" in defaults.TYPESCRIPT_EXTENSIONS
    assert ".tsx" in defaults.TYPESCRIPT_EXTENSIONS
    assert ".mts" in defaults.TYPESCRIPT_EXTENSIONS
    assert ".cts" in defaults.TYPESCRIPT_EXTENSIONS


def test_declaration_extensions() -> None:
    assert ".d.ts" in defaults.DECLARATION_EXTENSIONS


def test_tsconfig_filename() -> None:
    assert defaults.TSCONFIG_FILENAME == "tsconfig.json"


def test_adapter_entry_point_group() -> None:
    assert defaults.DEFAULT_ADAPTER_ENTRY_POINT_GROUP == "pytscheck.adapters"


def test_all_names_exist() -> None:
    for name in defaults.__all__:
        assert hasattr(defaults, name), f"missing: {name}"
