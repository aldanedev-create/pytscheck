"""Tests for the public API contract."""

from __future__ import annotations

import inspect

import pytest

import pytscheck
from pytscheck import check, check_file, check_project

# --- __all__ contract ------------------------------------------------------


def test_all_names_exist() -> None:
    for name in pytscheck.__all__:
        assert hasattr(pytscheck, name), f"missing: {name}"


def test_all_entries_are_class_callable_or_string() -> None:
    for name in pytscheck.__all__:
        obj = getattr(pytscheck, name)
        assert isinstance(obj, (type, str)) or callable(obj), (
            f"{name} is neither class, callable, nor string: {type(obj)}"
        )


def test_no_duplicate_names_in_all() -> None:
    assert len(pytscheck.__all__) == len(set(pytscheck.__all__))


def test_all_is_sorted_within_groups() -> None:
    """__all__ should have version constants first, then API, etc. Sanity check."""
    # Just ensure __version__ comes before API names
    i_ver = pytscheck.__all__.index("__version__")
    i_check = pytscheck.__all__.index("check")
    assert i_ver < i_check


# --- function signatures ---------------------------------------------------


def test_check_signature() -> None:
    sig = inspect.signature(check)
    assert list(sig.parameters) == ["source", "filename", "options", "keep_raw"]
    assert sig.parameters["source"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    for name in ("filename", "options", "keep_raw"):
        assert sig.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY


def test_check_file_signature() -> None:
    sig = inspect.signature(check_file)
    assert list(sig.parameters) == ["path", "options", "keep_raw"]
    assert sig.parameters["path"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_check_project_signature() -> None:
    sig = inspect.signature(check_project)
    assert list(sig.parameters) == ["project_root", "options", "adapter", "keep_raw"]
    assert sig.parameters["project_root"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


@pytest.mark.parametrize("name", ["check", "check_file", "check_project"])
def test_entry_points_have_return_annotation(name: str) -> None:
    fn = getattr(pytscheck, name)
    sig = inspect.signature(fn)
    assert sig.return_annotation is not inspect.Parameter.empty


@pytest.mark.parametrize("name", ["check", "check_file", "check_project"])
def test_entry_points_have_docstrings(name: str) -> None:
    fn = getattr(pytscheck, name)
    doc = inspect.getdoc(fn)
    assert doc, f"{name} has no docstring"
    assert "Type-check" in doc


# --- re-exports ------------------------------------------------------------


def test_version_constants_are_exposed() -> None:
    assert isinstance(pytscheck.__version__, str)
    assert isinstance(pytscheck.COMPILER_VERSION, str)
    assert isinstance(pytscheck.ADAPTER_PROTOCOL_VERSION, str)


def test_compiler_options_reexported() -> None:
    from pytscheck.config import CompilerOptions

    assert pytscheck.CompilerOptions is CompilerOptions


def test_models_reexported() -> None:
    from pytscheck.models import Diagnostic, RelatedInformation, Result, SourceFile

    assert pytscheck.Diagnostic is Diagnostic
    assert pytscheck.Result is Result
    assert pytscheck.SourceFile is SourceFile
    assert pytscheck.RelatedInformation is RelatedInformation


def test_exceptions_reexported() -> None:
    from pytscheck import exceptions

    assert pytscheck.PyTSCheckError is exceptions.PyTSCheckError
    assert pytscheck.CompilerNotFoundError is exceptions.CompilerNotFoundError
    assert pytscheck.CompilerExecutionError is exceptions.CompilerExecutionError
    assert pytscheck.CompilerTimeoutError is exceptions.CompilerTimeoutError
    assert pytscheck.OutputParseError is exceptions.OutputParseError
    assert pytscheck.ConfigurationError is exceptions.ConfigurationError
    assert pytscheck.AdapterError is exceptions.AdapterError
    assert pytscheck.AdapterExtractionError is exceptions.AdapterExtractionError
    assert pytscheck.AdapterMappingError is exceptions.AdapterMappingError
    assert pytscheck.AdapterProtocolError is exceptions.AdapterProtocolError
    assert pytscheck.AdapterRegistrationError is exceptions.AdapterRegistrationError
    assert pytscheck.AdapterDiscoveryError is exceptions.AdapterDiscoveryError


# --- end-to-end via the public surface (requires binary) -------------------


def test_check_via_public_api(tsgo_binary) -> None:
    r = pytscheck.check("export const x: number = 1;")
    assert r.success


def test_check_file_via_public_api(tsgo_binary, ts_file_valid) -> None:
    r = pytscheck.check_file(ts_file_valid)
    assert r.success


def test_check_project_via_public_api(tsgo_binary, project_minimal) -> None:
    r = pytscheck.check_project(project_minimal)
    assert r.success
