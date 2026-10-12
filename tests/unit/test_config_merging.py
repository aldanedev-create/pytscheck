"""Unit tests for combining user CompilerOptions with defaults."""

from __future__ import annotations

import pytest

from pytscheck.config import CompilerOptions


def test_defaults_when_no_overrides() -> None:
    o = CompilerOptions()
    assert o.strict is True
    assert o.no_emit is True
    assert o.skip_lib_check is False


def test_explicit_overrides_take_precedence() -> None:
    o = CompilerOptions(strict=False, no_emit=False, skip_lib_check=True)
    assert o.strict is False
    assert o.no_emit is False
    assert o.skip_lib_check is True


def test_extra_field_defaults_empty() -> None:
    assert CompilerOptions().extra == {}


def test_extra_field_preserves_values() -> None:
    o = CompilerOptions(extra={"outDir": "dist", "pretty": True})
    assert o.extra == {"outDir": "dist", "pretty": True}


def test_two_instances_have_independent_extra_dicts() -> None:
    a = CompilerOptions()
    b = CompilerOptions()
    assert a.extra is not b.extra


def test_multiple_tuple_fields_independent() -> None:
    a = CompilerOptions(types=("x",))
    b = CompilerOptions(lib=("y",))
    assert a.types == ("x",)
    assert a.lib == ()
    assert b.lib == ("y",)
    assert b.types == ()


def test_options_are_frozen() -> None:
    import dataclasses

    o = CompilerOptions()
    with pytest.raises(dataclasses.FrozenInstanceError):
        o.strict = False  # type: ignore[misc]


def test_options_are_equatable() -> None:
    a = CompilerOptions()
    b = CompilerOptions()
    assert a == b


def test_options_with_different_extra_are_not_equal() -> None:
    a = CompilerOptions(extra={"x": True})
    b = CompilerOptions()
    assert a != b


def test_options_are_hashable() -> None:
    o = CompilerOptions()
    with pytest.raises(TypeError):
        hash(o)


def test_options_with_extra_dict_are_hashable_if_dict_is_not() -> None:
    """dict is not hashable; CompilerOptions containing a dict is not either.

    This documents the design decision: CompilerOptions is not intended to
    be used as a dict key. If hashability is required, callers should
    convert extra to a frozenset of items.
    """
    o = CompilerOptions(extra={"x": True})
    with pytest.raises(TypeError):
        hash(o)


def test_dataclass_replace_produces_new_instance() -> None:
    import dataclasses

    a = CompilerOptions()
    b = dataclasses.replace(a, strict=False)
    assert a.strict is True
    assert b.strict is False
    assert a is not b


def test_replace_does_not_share_extra_dict() -> None:
    import dataclasses

    a = CompilerOptions(extra={"x": 1})
    b = dataclasses.replace(a, strict=False)
    # dataclasses.replace carries supplied fields into the new instance
    assert a.extra == b.extra
    # Mutable fields are shared; replacement does not promise a deep copy
    b.extra["y"] = 2  # type: ignore[index]
    assert b.extra is a.extra
    assert a.extra["y"] == 2
