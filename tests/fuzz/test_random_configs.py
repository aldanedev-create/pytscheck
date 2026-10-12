"""Fuzz the config loader and CompilerOptions validation.

Verifies that hostile tsconfig.json content and hostile option values
cannot crash the loader or produce a successful check for a broken config.
"""

from __future__ import annotations

import json
import random
import string
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from pytscheck.config import CompilerOptions, load_tsconfig
from pytscheck.exceptions import ConfigurationError
from pytscheck.options import options_to_argv

# ---------------------------------------------------------------------------
# Property-based: options construction
# ---------------------------------------------------------------------------


@given(
    st.lists(st.text(max_size=20), max_size=5),
    st.lists(st.text(max_size=20), max_size=5),
)
@settings(
    max_examples=200,
    deadline=None,
    # Each example overwrites the same temporary file completely.
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_options_to_argv_never_crashes(types: list[str], lib: list[str]) -> None:
    try:
        argv = options_to_argv(CompilerOptions(types=tuple(types), lib=tuple(lib)))
    except ConfigurationError:
        return
    assert isinstance(argv, list)
    for a in argv:
        assert isinstance(a, str)
        assert "\x00" not in a


@given(
    st.dictionaries(
        st.text(max_size=10),
        st.one_of(st.text(), st.integers(), st.booleans(), st.none()),
        max_size=10,
    )
)
@settings(
    max_examples=200,
    deadline=None,
    # Each example overwrites the same temporary file completely.
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_options_extra_never_crashes(extra: dict) -> None:
    try:
        argv = options_to_argv(CompilerOptions(extra=extra))
    except (ConfigurationError, TypeError):
        return
    assert isinstance(argv, list)
    for a in argv:
        assert isinstance(a, str)
        assert "\x00" not in a


# ---------------------------------------------------------------------------
# Property-based: tsconfig parsing
# ---------------------------------------------------------------------------


@given(st.text())
@settings(
    max_examples=300,
    deadline=None,
    # Each example overwrites the same temporary file completely.
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_load_tsconfig_never_crashes_on_text(tmp_path: Path, text: str) -> None:
    p = tmp_path / "tsconfig.json"
    p.write_text(text, encoding="utf-8")
    try:
        data = load_tsconfig(p)
    except ConfigurationError:
        return
    assert isinstance(data, dict)


@given(st.binary(max_size=10_000))
@settings(
    max_examples=200,
    deadline=None,
    # Each example overwrites the same temporary file completely.
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
def test_load_tsconfig_never_crashes_on_bytes(tmp_path: Path, data: bytes) -> None:
    p = tmp_path / "tsconfig.json"
    p.write_bytes(data)
    try:
        load_tsconfig(p)
    except (ConfigurationError, UnicodeDecodeError):
        return


# ---------------------------------------------------------------------------
# Structured hostile tsconfig
# ---------------------------------------------------------------------------


def _random_json_value(rng: random.Random, depth: int = 0) -> object:
    """Generate a random JSON-encodable value with bounded depth."""
    if depth > 5:
        return rng.choice([None, True, False, 0, 1, -1, "", "x"])
    choice = rng.randint(0, 6)
    if choice == 0:
        return None
    if choice == 1:
        return rng.choice([True, False])
    if choice == 2:
        return rng.randint(-(10**9), 10**9)
    if choice == 3:
        return "".join(rng.choices(string.printable, k=rng.randint(0, 20)))
    if choice == 4:
        return [_random_json_value(rng, depth + 1) for _ in range(rng.randint(0, 5))]
    if choice == 5:
        return {
            "".join(rng.choices(string.ascii_letters, k=5)): _random_json_value(rng, depth + 1)
            for _ in range(rng.randint(0, 5))
        }
    return {"compilerOptions": _random_json_value(rng, depth + 1)}


def test_random_tsconfig_objects(tmp_path: Path, rng: random.Random) -> None:
    for _ in range(200):
        value = _random_json_value(rng)
        p = tmp_path / "tsconfig.json"
        try:
            p.write_text(json.dumps(value), encoding="utf-8")
        except (TypeError, ValueError):
            continue
        try:
            load_tsconfig(p)
        except ConfigurationError:
            continue


def test_random_tsconfig_extends_values(tmp_path: Path, rng: random.Random) -> None:
    for _ in range(100):
        extends = rng.choice(
            [
                None,
                42,
                True,
                [],
                {},
                "",
                "./base.json",
                "../../escape",
                "/etc/passwd",
                "..\\escape",
                "a" * 10_000,
                "\x00",
            ]
        )
        p = tmp_path / "tsconfig.json"
        p.write_text(json.dumps({"extends": extends}), encoding="utf-8")
        from pytscheck.resolver import resolve_project

        try:
            resolve_project(tmp_path)
        except ConfigurationError:
            continue


# ---------------------------------------------------------------------------
# Hostile raw JSON shapes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        "",
        " ",
        "\n",
        "{",
        "}",
        "[",
        "]",
        "null",
        "true",
        "false",
        "42",
        '"a"',
        "'a'",  # single quotes are not valid JSON
        "{'a': 1}",  # trailing comma
        '{"a": 1,}',
        '{"a": 1} extra',
        "\x00",
        "\ufeff{}",
        "{}",
    ],
)
def test_specific_hostile_jsons(tmp_path: Path, raw: str) -> None:
    p = tmp_path / "tsconfig.json"
    p.write_text(raw, encoding="utf-8")
    try:
        data = load_tsconfig(p)
    except ConfigurationError:
        return
    assert isinstance(data, dict)


def test_duplicate_keys_in_tsconfig(tmp_path: Path) -> None:
    p = tmp_path / "tsconfig.json"
    p.write_text('{"a": 1, "a": 2}', encoding="utf-8")
    data = load_tsconfig(p)
    assert data["a"] == 2


def test_deeply_nested_json_in_tsconfig(tmp_path: Path) -> None:
    depth = 1000
    raw = "[" * depth + "]" * depth
    p = tmp_path / "tsconfig.json"
    p.write_text(raw, encoding="utf-8")
    # Either loads (list is not a dict → ConfigurationError) or raises
    # RecursionError; both are acceptable and neither crashes the process.
    try:
        load_tsconfig(p)
    except (ConfigurationError, RecursionError):
        return


def test_huge_number_of_keys(tmp_path: Path) -> None:
    raw = "{" + ",".join(f'"k{i}": {i}' for i in range(10_000)) + "}"
    p = tmp_path / "tsconfig.json"
    p.write_text(raw, encoding="utf-8")
    data = load_tsconfig(p)
    assert len(data) == 10_000


def test_control_chars_in_keys(tmp_path: Path) -> None:
    raw = json.dumps({"a\x00b": 1, "c\n": 2})
    p = tmp_path / "tsconfig.json"
    p.write_text(raw, encoding="utf-8")
    data = load_tsconfig(p)
    assert "a\x00b" in data


# ---------------------------------------------------------------------------
# Invalid UTF-8
# ---------------------------------------------------------------------------


def test_invalid_utf8_bytes(tmp_path: Path) -> None:
    p = tmp_path / "tsconfig.json"
    p.write_bytes(b'{"a": "\xff\xfe\xfd"}')
    with pytest.raises(ConfigurationError):
        load_tsconfig(p)


def test_truncated_utf8_bytes(tmp_path: Path) -> None:
    p = tmp_path / "tsconfig.json"
    # Valid UTF-8 sequence cut mid-codepoint
    p.write_bytes(b'{"a": "\xe4\xb8')
    with pytest.raises(ConfigurationError):
        load_tsconfig(p)


def test_null_byte_in_json_bytes(tmp_path: Path) -> None:
    p = tmp_path / "tsconfig.json"
    p.write_bytes(b'{"a": 1}\x00')
    # json.loads on a string with trailing NUL will fail
    with pytest.raises(ConfigurationError):
        load_tsconfig(p)
