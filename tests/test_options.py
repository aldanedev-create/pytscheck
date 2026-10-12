"""Tests for pytscheck.options."""

from __future__ import annotations

import pytest

from pytscheck.config import CompilerOptions
from pytscheck.exceptions import ConfigurationError
from pytscheck.options import options_to_argv


def test_defaults_emit_no_emit_and_strict() -> None:
    argv = options_to_argv(CompilerOptions())
    assert "--noEmit" in argv
    assert "--strict" in argv


def test_no_emit_false_omits_flag() -> None:
    assert "--noEmit" not in options_to_argv(CompilerOptions(no_emit=False))


def test_strict_false_omits_flag() -> None:
    assert "--strict" not in options_to_argv(CompilerOptions(strict=False))


def test_skip_lib_check_true_adds_flag() -> None:
    assert "--skipLibCheck" in options_to_argv(CompilerOptions(skip_lib_check=True))


def test_skip_lib_check_false_omits_flag() -> None:
    assert "--skipLibCheck" not in options_to_argv(CompilerOptions(skip_lib_check=False))


def test_types_list_becomes_comma_separated_flag() -> None:
    argv = options_to_argv(CompilerOptions(types=("node", "jest")))
    assert argv.count("--types") == 1
    assert argv[argv.index("--types") + 1] == "node,jest"


def test_lib_list_becomes_comma_separated_flag() -> None:
    argv = options_to_argv(CompilerOptions(lib=("es2022", "dom")))
    assert argv.count("--lib") == 1
    assert argv[argv.index("--lib") + 1] == "es2022,dom"


def test_target_and_module_and_resolution() -> None:
    argv = options_to_argv(
        CompilerOptions(
            target="es2022",
            module="esnext",
            module_resolution="bundler",
        )
    )
    assert "--target" in argv and "es2022" in argv
    assert "--module" in argv and "esnext" in argv
    assert "--moduleResolution" in argv and "bundler" in argv


def test_extra_boolean_true_emits_flag() -> None:
    assert "--pretty" in options_to_argv(CompilerOptions(extra={"pretty": True}))


def test_extra_boolean_false_omits_flag() -> None:
    assert "--pretty" not in options_to_argv(CompilerOptions(extra={"pretty": False}))


def test_extra_none_omits_flag() -> None:
    assert "--pretty" not in options_to_argv(CompilerOptions(extra={"pretty": None}))


def test_extra_string_becomes_key_value() -> None:
    argv = options_to_argv(CompilerOptions(extra={"outDir": "dist"}))
    assert "--outDir" in argv
    idx = argv.index("--outDir")
    assert argv[idx + 1] == "dist"


def test_extra_key_with_leading_dashes_is_preserved() -> None:
    argv = options_to_argv(CompilerOptions(extra={"--pretty": True}))
    assert argv.count("--pretty") == 1


def test_extra_integer_becomes_key_value() -> None:
    argv = options_to_argv(CompilerOptions(extra={"maxNodeModuleJsDepth": 5}))
    assert "--maxNodeModuleJsDepth" in argv
    idx = argv.index("--maxNodeModuleJsDepth")
    assert argv[idx + 1] == "5"


def test_null_byte_in_types_raises() -> None:
    with pytest.raises(ConfigurationError, match="NUL"):
        options_to_argv(CompilerOptions(types=("ok\x00bad",)))


def test_null_byte_in_lib_raises() -> None:
    with pytest.raises(ConfigurationError, match="NUL"):
        options_to_argv(CompilerOptions(lib=("ok\x00bad",)))


def test_null_byte_in_target_raises() -> None:
    with pytest.raises(ConfigurationError, match="NUL"):
        options_to_argv(CompilerOptions(target="es\x002022"))


def test_null_byte_in_extra_key_raises() -> None:
    with pytest.raises(ConfigurationError, match="NUL"):
        options_to_argv(CompilerOptions(extra={"x\x00y": True}))


def test_null_byte_in_extra_value_raises() -> None:
    with pytest.raises(ConfigurationError, match="NUL"):
        options_to_argv(CompilerOptions(extra={"x": "a\x00b"}))


def test_argv_is_list_of_strings() -> None:
    argv = options_to_argv(CompilerOptions())
    assert isinstance(argv, list)
    assert all(isinstance(a, str) for a in argv)


def test_argv_never_contains_nul_bytes() -> None:
    argv = options_to_argv(
        CompilerOptions(
            types=("a", "b"),
            lib=("es2022",),
            target="es2022",
            extra={"pretty": True},
        )
    )
    for a in argv:
        assert "\x00" not in a
