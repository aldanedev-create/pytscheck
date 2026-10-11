"""Unit tests for CompilerOptions validation and argv construction."""

from __future__ import annotations

import pytest

from pytscheck.config import CompilerOptions
from pytscheck.exceptions import ConfigurationError
from pytscheck.options import options_to_argv


# --- type validation --------------------------------------------------------


def test_types_must_be_tuple_of_strings() -> None:
    # A list is accepted at dataclass level but treated as iterable
    o = CompilerOptions(types=("a", "b"))
    argv = options_to_argv(o)
    assert argv.count("--types") == 2


def test_types_with_non_string_raises_at_argv_time() -> None:
    o = CompilerOptions(types=(1, 2))  # type: ignore[arg-type]
    with pytest.raises((TypeError, ConfigurationError)):
        options_to_argv(o)


def test_empty_types_list_produces_no_flag() -> None:
    argv = options_to_argv(CompilerOptions(types=()))
    assert "--types" not in argv


def test_empty_lib_list_produces_no_flag() -> None:
    argv = options_to_argv(CompilerOptions(lib=()))
    assert "--lib" not in argv


# --- null byte rejection ---------------------------------------------------


def test_types_reject_nul() -> None:
    with pytest.raises(ConfigurationError):
        options_to_argv(CompilerOptions(types=("ok\x00",)))


def test_lib_rejects_nul() -> None:
    with pytest.raises(ConfigurationError):
        options_to_argv(CompilerOptions(lib=("\x00",)))


def test_target_rejects_nul() -> None:
    with pytest.raises(ConfigurationError):
        options_to_argv(CompilerOptions(target="e\x00s"))


def test_module_rejects_nul() -> None:
    with pytest.raises(ConfigurationError):
        options_to_argv(CompilerOptions(module="es\x00"))


def test_extra_key_rejects_nul() -> None:
    with pytest.raises(ConfigurationError):
        options_to_argv(CompilerOptions(extra={"a\x00": True}))


def test_extra_value_rejects_nul() -> None:
    with pytest.raises(ConfigurationError):
        options_to_argv(CompilerOptions(extra={"a": "b\x00"}))


# --- extra option handling -------------------------------------------------


def test_extra_true_emits_flag_only() -> None:
    argv = options_to_argv(CompilerOptions(extra={"pretty": True}))
    assert "--pretty" in argv
    i = argv.index("--pretty")
    # No value follows, or the next token is another flag
    assert i == len(argv) - 1 or argv[i + 1].startswith("--")


def test_extra_false_skips_flag() -> None:
    assert "--pretty" not in options_to_argv(CompilerOptions(extra={"pretty": False}))


def test_extra_none_skips_flag() -> None:
    assert "--pretty" not in options_to_argv(CompilerOptions(extra={"pretty": None}))


def test_extra_string_emits_key_value() -> None:
    argv = options_to_argv(CompilerOptions(extra={"outDir": "dist"}))
    i = argv.index("--outDir")
    assert argv[i + 1] == "dist"


def test_extra_integer_emits_key_value() -> None:
    argv = options_to_argv(CompilerOptions(extra={"depth": 5}))
    i = argv.index("--depth")
    assert argv[i + 1] == "5"


def test_extra_key_with_double_dash_preserved() -> None:
    argv = options_to_argv(CompilerOptions(extra={"--pretty": True}))
    assert argv.count("--pretty") == 1


def test_extra_multiple_options_ordered() -> None:
    argv = options_to_argv(
        CompilerOptions(extra={"a": True, "b": "x", "c": False, "d": "y"})
    )
    # All truthy keys present
    assert "--a" in argv
    assert "--b" in argv and "x" in argv
    assert "--d" in argv and "y" in argv
    assert "--c" not in argv


# --- strict/no_emit defaults ------------------------------------------------


def test_default_strict_on() -> None:
    assert "--strict" in options_to_argv(CompilerOptions())


def test_default_no_emit_on() -> None:
    assert "--noEmit" in options_to_argv(CompilerOptions())


def test_strict_can_be_disabled() -> None:
    assert "--strict" not in options_to_argv(CompilerOptions(strict=False))


def test_no_emit_can_be_disabled() -> None:
    assert "--noEmit" not in options_to_argv(CompilerOptions(no_emit=False))


# --- return shape ----------------------------------------------------------


def test_returns_list_of_str() -> None:
    argv = options_to_argv(CompilerOptions())
    assert isinstance(argv, list)
    assert all(isinstance(a, str) for a in argv)


def test_never_returns_empty_for_default_options() -> None:
    assert options_to_argv(CompilerOptions())