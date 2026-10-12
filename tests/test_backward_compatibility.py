"""Tests that the public API is not accidentally broken."""

from __future__ import annotations

import inspect

import pytscheck


def test_check_has_expected_parameters() -> None:
    sig = inspect.signature(pytscheck.check)
    assert set(sig.parameters) == {"source", "filename", "options", "keep_raw"}


def test_check_file_has_expected_parameters() -> None:
    sig = inspect.signature(pytscheck.check_file)
    assert set(sig.parameters) == {"path", "options", "keep_raw"}


def test_check_project_has_expected_parameters() -> None:
    sig = inspect.signature(pytscheck.check_project)
    assert set(sig.parameters) == {"project_root", "options", "adapter", "keep_raw"}


def test_defaults_are_unchanged() -> None:
    sig = inspect.signature(pytscheck.check)
    assert sig.parameters["filename"].default == "input.ts"
    assert sig.parameters["options"].default is None
    assert sig.parameters["keep_raw"].default is False


def test_public_names_are_stable() -> None:
    """Names that must remain in __all__ forever (until a major bump)."""
    required = {
        "__version__",
        "COMPILER_VERSION",
        "ADAPTER_PROTOCOL_VERSION",
        "check",
        "check_file",
        "check_project",
        "CompilerOptions",
        "Result",
        "Diagnostic",
        "RelatedInformation",
        "SourceFile",
        "PyTSCheckError",
        "UnsupportedPlatformError",
        "CompilerNotFoundError",
        "CompilerExecutionError",
        "CompilerTimeoutError",
        "OutputParseError",
        "ConfigurationError",
        "AdapterError",
        "AdapterDiscoveryError",
        "AdapterExtractionError",
        "AdapterMappingError",
        "AdapterProtocolError",
        "AdapterRegistrationError",
    }
    assert required.issubset(set(pytscheck.__all__))


def test_result_fields_are_stable() -> None:
    import dataclasses

    from pytscheck.models import Result

    fields = {f.name for f in dataclasses.fields(Result)}
    assert {"success", "diagnostics", "compiler_version", "elapsed_seconds"}.issubset(fields)
    # raw_output is optional
    assert "raw_output" in fields


def test_diagnostic_fields_are_stable() -> None:
    import dataclasses

    from pytscheck.models import Diagnostic

    fields = {f.name for f in dataclasses.fields(Diagnostic)}
    required = {
        "file",
        "line",
        "column",
        "code",
        "category",
        "message",
        "end_line",
        "end_column",
        "related",
        "origin_file",
    }
    assert required.issubset(fields)


def test_source_file_fields_are_stable() -> None:
    import dataclasses

    from pytscheck.models import SourceFile

    fields = {f.name for f in dataclasses.fields(SourceFile)}
    required = {"path", "text", "origin_path", "source_map", "kind", "options"}
    assert required.issubset(fields)


def test_compiler_options_fields_are_stable() -> None:
    import dataclasses

    from pytscheck.config import CompilerOptions

    fields = {f.name for f in dataclasses.fields(CompilerOptions)}
    required = {
        "strict",
        "no_emit",
        "skip_lib_check",
        "types",
        "lib",
        "target",
        "module",
        "module_resolution",
        "extra",
    }
    assert required.issubset(fields)


def test_exception_hierarchy_is_stable() -> None:
    from pytscheck.exceptions import (
        AdapterError,
        CompilerNotFoundError,
        CompilerTimeoutError,
        PyTSCheckError,
    )

    assert issubclass(PyTSCheckError, Exception)
    assert issubclass(CompilerNotFoundError, PyTSCheckError)
    assert issubclass(CompilerTimeoutError, PyTSCheckError)
    assert issubclass(AdapterError, PyTSCheckError)


def test_adapter_protocol_methods_are_stable() -> None:
    from pytscheck.adapters.base import CompilerAdapter

    # Protocol declares `name` and `get_sources`
    assert "get_sources" in dir(CompilerAdapter) or "get_sources" in str(CompilerAdapter.__dict__)
