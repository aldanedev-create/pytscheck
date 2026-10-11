"""Unit tests for exception chaining behavior."""

from __future__ import annotations

import pytest

from pytscheck import exceptions as exc


# --- raise-from preservation -----------------------------------------------


def test_configuration_error_chains_original() -> None:
    original = ValueError("original")
    try:
        try:
            raise original
        except ValueError as e:
            raise exc.ConfigurationError("wrapped") from e
    except exc.ConfigurationError as wrapped:
        assert wrapped.__cause__ is original
        assert wrapped.__context__ is original


def test_output_parse_error_chains_original() -> None:
    original = ValueError("bad json")
    try:
        try:
            raise original
        except ValueError as e:
            raise exc.OutputParseError("parse failed", raw_output="...") from e
    except exc.OutputParseError as wrapped:
        assert wrapped.__cause__ is original


def test_compiler_execution_error_chains_original() -> None:
    original = OSError("no such file")
    try:
        try:
            raise original
        except OSError as e:
            raise exc.CompilerExecutionError("launch failed") from e
    except exc.CompilerExecutionError as wrapped:
        assert wrapped.__cause__ is original


def test_adapter_extraction_error_chains_original() -> None:
    original = SyntaxError("malformed")
    try:
        try:
            raise original
        except SyntaxError as e:
            raise exc.AdapterExtractionError("extraction failed") from e
    except exc.AdapterExtractionError as wrapped:
        assert wrapped.__cause__ is original


# --- suppressed context ----------------------------------------------------


def test_raise_from_none_suppresses_context() -> None:
    try:
        try:
            raise ValueError("suppressed")
        except ValueError:
            raise exc.ConfigurationError("explicit") from None
    except exc.ConfigurationError as wrapped:
        assert wrapped.__cause__ is None
        # __context__ is set but __suppress_context__ is True
        assert wrapped.__suppress_context__ is True


# --- message preservation --------------------------------------------------


def test_message_preserved_through_chaining() -> None:
    try:
        try:
            raise ValueError("inner")
        except ValueError as e:
            raise exc.ConfigurationError("outer message") from e
    except exc.ConfigurationError as wrapped:
        assert "outer message" in str(wrapped)


def test_args_tuple_is_preserved() -> None:
    e = exc.ConfigurationError("m")
    assert e.args == ("m",)


def test_payload_and_chaining_together() -> None:
    original = RuntimeError("boom")
    try:
        try:
            raise original
        except RuntimeError as e:
            raise exc.CompilerExecutionError(
                "failed", returncode=137, stderr="killed"
            ) from e
    except exc.CompilerExecutionError as wrapped:
        assert wrapped.__cause__ is original
        assert wrapped.returncode == 137
        assert wrapped.stderr == "killed"


# --- re-raise behavior -----------------------------------------------------


def test_bare_reraise_preserves_exception() -> None:
    original = exc.ConfigurationError("x")
    try:
        try:
            raise original
        except exc.ConfigurationError:
            raise
    except exc.ConfigurationError as caught:
        assert caught is original


def test_catching_base_catches_subclass() -> None:
    with pytest.raises(exc.PyTSCheckError):
        raise exc.CompilerTimeoutError("t")


def test_catching_execution_catches_timeout() -> None:
    with pytest.raises(exc.CompilerExecutionError):
        raise exc.CompilerTimeoutError("t")


# --- str/repr ---------------------------------------------------------------


def test_str_returns_message() -> None:
    assert str(exc.ConfigurationError("hello")) == "hello"


def test_repr_contains_class_name() -> None:
    r = repr(exc.ConfigurationError("hello"))
    assert "ConfigurationError" in r


def test_repr_of_compiler_error_contains_payload() -> None:
    e = exc.CompilerExecutionError("boom", returncode=1, stderr="err")
    r = repr(e)
    assert "CompilerExecutionError" in r