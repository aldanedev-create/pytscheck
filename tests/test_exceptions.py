"""Tests for pytscheck.exceptions."""

from __future__ import annotations

import pytest

from pytscheck import exceptions as exc


def test_all_names_are_classes_deriving_from_base() -> None:
    for name in exc.__all__:
        obj = getattr(exc, name)
        assert isinstance(obj, type), f"{name} is not a class"
        assert issubclass(obj, exc.PyTSCheckError), f"{name} does not derive from base"


def test_compiler_hierarchy() -> None:
    assert issubclass(exc.UnsupportedPlatformError, exc.PyTSCheckError)
    assert issubclass(exc.CompilerNotFoundError, exc.PyTSCheckError)
    assert issubclass(exc.CompilerExecutionError, exc.PyTSCheckError)
    assert issubclass(exc.CompilerTimeoutError, exc.CompilerExecutionError)
    assert issubclass(exc.OutputParseError, exc.PyTSCheckError)
    assert issubclass(exc.ConfigurationError, exc.PyTSCheckError)


def test_adapter_hierarchy() -> None:
    assert issubclass(exc.AdapterError, exc.PyTSCheckError)
    assert issubclass(exc.AdapterRegistrationError, exc.AdapterError)
    assert issubclass(exc.AdapterDiscoveryError, exc.AdapterError)
    assert issubclass(exc.AdapterExtractionError, exc.AdapterError)
    assert issubclass(exc.AdapterMappingError, exc.AdapterError)
    assert issubclass(exc.AdapterProtocolError, exc.AdapterError)


def test_adapter_errors_are_not_compiler_errors() -> None:
    assert not issubclass(exc.AdapterError, exc.CompilerExecutionError)
    assert not issubclass(exc.AdapterError, exc.CompilerNotFoundError)
    assert not issubclass(exc.AdapterExtractionError, exc.CompilerExecutionError)


def test_compiler_execution_error_carries_payload() -> None:
    e = exc.CompilerExecutionError(
        "boom", returncode=137, stdout="out", stderr="err"
    )
    assert e.returncode == 137
    assert e.stdout == "out"
    assert e.stderr == "err"
    assert "boom" in str(e)


def test_compiler_execution_error_payload_is_optional() -> None:
    e = exc.CompilerExecutionError("boom")
    assert e.returncode is None
    assert e.stdout is None
    assert e.stderr is None


def test_compiler_timeout_is_catchable_as_execution_error() -> None:
    with pytest.raises(exc.CompilerExecutionError):
        raise exc.CompilerTimeoutError("too slow")


def test_output_parse_error_carries_raw_output() -> None:
    e = exc.OutputParseError("bad", raw_output="xxx")
    assert e.raw_output == "xxx"


def test_output_parse_error_raw_output_optional() -> None:
    e = exc.OutputParseError("bad")
    assert e.raw_output is None


def test_adapter_extraction_error_message_preserved() -> None:
    e = exc.AdapterExtractionError("no <script> block found in Button.vel")
    assert "no <script> block found" in str(e)


def test_every_exception_can_be_raised_and_caught_as_base() -> None:
    for name in exc.__all__:
        cls = getattr(exc, name)
        with pytest.raises(exc.PyTSCheckError):
            raise cls("test")


def test_exception_chaining_preserved() -> None:
    """`raise X from Y` must preserve the cause."""
    original = ValueError("original")
    try:
        try:
            raise original
        except ValueError as e:
            raise exc.ConfigurationError("wrapped") from e
    except exc.ConfigurationError as wrapped:
        assert wrapped.__cause__ is original


def test_slots_prevent_attribute_sprawl_on_payload_classes() -> None:
    e = exc.CompilerExecutionError("boom", returncode=1)
    with pytest.raises(AttributeError):
        e.undeclared = 1  # type: ignore[attr-defined]

    e2 = exc.OutputParseError("bad")
    with pytest.raises(AttributeError):
        e2.undeclared = 1  # type: ignore[attr-defined]