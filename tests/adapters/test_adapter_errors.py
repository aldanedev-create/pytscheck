"""Tests for the adapter exception hierarchy and its behavior."""

from __future__ import annotations

import pytest

from pytscheck import exceptions as exc


# --- hierarchy --------------------------------------------------------------


def test_all_adapter_errors_derive_from_adapter_error() -> None:
    for name in (
        "AdapterRegistrationError",
        "AdapterDiscoveryError",
        "AdapterExtractionError",
        "AdapterMappingError",
        "AdapterProtocolError",
    ):
        cls = getattr(exc, name)
        assert issubclass(cls, exc.AdapterError), name


def test_adapter_error_derives_from_base() -> None:
    assert issubclass(exc.AdapterError, exc.PyTSCheckError)


def test_adapter_errors_are_not_compiler_errors() -> None:
    for name in (
        "AdapterRegistrationError",
        "AdapterDiscoveryError",
        "AdapterExtractionError",
        "AdapterMappingError",
        "AdapterProtocolError",
    ):
        cls = getattr(exc, name)
        assert not issubclass(cls, exc.CompilerExecutionError)
        assert not issubclass(cls, exc.CompilerNotFoundError)


# --- extraction vs protocol vs mapping --------------------------------------


def test_extraction_error_is_distinct_from_protocol_error() -> None:
    assert not issubclass(exc.AdapterExtractionError, exc.AdapterProtocolError)
    assert not issubclass(exc.AdapterProtocolError, exc.AdapterExtractionError)


def test_mapping_error_is_distinct_from_extraction_error() -> None:
    assert not issubclass(exc.AdapterMappingError, exc.AdapterExtractionError)
    assert not issubclass(exc.AdapterExtractionError, exc.AdapterMappingError)


def test_registration_error_is_distinct_from_discovery_error() -> None:
    assert not issubclass(exc.AdapterRegistrationError, exc.AdapterDiscoveryError)
    assert not issubclass(exc.AdapterDiscoveryError, exc.AdapterRegistrationError)


# --- messages ---------------------------------------------------------------


def test_extraction_error_message_preserved() -> None:
    e = exc.AdapterExtractionError("no <script> block in Button.vel")
    assert "no <script> block" in str(e)


def test_mapping_error_message_preserved() -> None:
    e = exc.AdapterMappingError("bad source map")
    assert "bad source map" in str(e)


def test_protocol_error_message_preserved() -> None:
    e = exc.AdapterProtocolError("adapter returned non-SourceFile")
    assert "non-SourceFile" in str(e)


def test_registration_error_message_preserved() -> None:
    e = exc.AdapterRegistrationError("adapter already registered: teloc")
    assert "teloc" in str(e)


def test_discovery_error_message_preserved() -> None:
    e = exc.AdapterDiscoveryError("entry point failed to load")
    assert "entry point" in str(e)


# --- catchability -----------------------------------------------------------


def test_can_catch_adapter_error_family() -> None:
    with pytest.raises(exc.AdapterError):
        raise exc.AdapterExtractionError("x")

    with pytest.raises(exc.AdapterError):
        raise exc.AdapterMappingError("x")

    with pytest.raises(exc.AdapterError):
        raise exc.AdapterProtocolError("x")

    with pytest.raises(exc.AdapterError):
        raise exc.AdapterRegistrationError("x")

    with pytest.raises(exc.AdapterError):
        raise exc.AdapterDiscoveryError("x")


def test_can_catch_pytscheckerror_family() -> None:
    for name in (
        "AdapterError",
        "AdapterRegistrationError",
        "AdapterDiscoveryError",
        "AdapterExtractionError",
        "AdapterMappingError",
        "AdapterProtocolError",
    ):
        with pytest.raises(exc.PyTSCheckError):
            raise getattr(exc, name)("x")


def test_cannot_catch_adapter_error_as_compiler_error() -> None:
    with pytest.raises(exc.AdapterError):
        try:
            raise exc.AdapterExtractionError("x")
        except exc.CompilerExecutionError:  # pragma: no cover
            raise AssertionError("adapter error caught as compiler error")