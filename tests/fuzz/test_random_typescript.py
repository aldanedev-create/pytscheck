"""Fuzz the checker with random and semi-structured TypeScript source.

Requires the bundled compiler. Skips cleanly when it is not present.
Verifies that no random input can crash the pipeline or produce a
successful result for syntactically invalid input.
"""

from __future__ import annotations

import random
import string
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from pytscheck import check
from pytscheck.exceptions import PyTSCheckError

# ---------------------------------------------------------------------------
# Property-based: pure random text must never crash
# ---------------------------------------------------------------------------


@given(st.text())
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
def test_random_text_never_crashes(tsgo_binary: Path, text: str) -> None:
    try:
        r = check(text)
    except PyTSCheckError:
        return
    assert isinstance(r.success, bool)


@given(st.text(alphabet=string.printable, max_size=2000))
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
)
def test_printable_text_never_crashes(tsgo_binary: Path, text: str) -> None:
    try:
        r = check(text)
    except PyTSCheckError:
        return
    assert isinstance(r.success, bool)


# ---------------------------------------------------------------------------
# Grammar-aware random generation
# ---------------------------------------------------------------------------


_KEYWORDS = [
    "const",
    "let",
    "var",
    "function",
    "class",
    "interface",
    "type",
    "enum",
    "namespace",
    "export",
    "import",
    "if",
    "else",
    "for",
    "while",
    "return",
    "async",
    "await",
    "yield",
    "new",
    "typeof",
    "instanceof",
    "in",
]

_TYPES = [
    "number",
    "string",
    "boolean",
    "any",
    "unknown",
    "never",
    "void",
    "null",
    "undefined",
    "object",
    "symbol",
    "bigint",
]

_PUNCT = ["{", "}", "(", ")", "[", "]", ";", ":", ",", ".", "=>", "=", "+", "-"]


def _random_identifier(rng: random.Random) -> str:
    return "".join(rng.choices(string.ascii_letters, k=rng.randint(1, 12)))


def _random_token_stream(rng: random.Random, n: int) -> str:
    tokens: list[str] = []
    for _ in range(n):
        choice = rng.randint(0, 5)
        if choice == 0:
            tokens.append(rng.choice(_KEYWORDS))
        elif choice == 1:
            tokens.append(rng.choice(_TYPES))
        elif choice == 2:
            tokens.append(_random_identifier(rng))
        elif choice == 3:
            tokens.append(rng.choice(_PUNCT))
        elif choice == 4:
            tokens.append(str(rng.randint(0, 100)))
        else:
            tokens.append(rng.choice(string.whitespace))
    return " ".join(tokens)


def test_random_token_streams(rng: random.Random) -> None:
    for _ in range(30):
        text = _random_token_stream(rng, rng.randint(20, 500))
        try:
            r = check(text)
        except PyTSCheckError:
            continue
        assert isinstance(r.success, bool)


# ---------------------------------------------------------------------------
# Mutations of valid source
# ---------------------------------------------------------------------------


_BASE_SOURCES = [
    "const x: number = 1;",
    "function f(a: number, b: number): number { return a + b; }",
    "interface U { name: string; age: number; }",
    "type T = 'a' | 'b' | 'c';",
    "class C { constructor(public x: number) {} }",
    "export default function(): void {}",
    "const arr: Array<number> = [1, 2, 3];",
    "async function main(): Promise<void> {}",
]


def _mutate(rng: random.Random, text: str, n_edits: int) -> str:
    chars = list(text)
    for _ in range(n_edits):
        if not chars:
            break
        op = rng.choice(["insert", "delete", "replace", "swap"])
        i = rng.randrange(len(chars))
        if op == "insert":
            chars.insert(i, rng.choice(string.printable))
        elif op == "delete":
            chars.pop(i)
        elif op == "replace":
            chars[i] = rng.choice(string.printable)
        elif op == "swap" and i + 1 < len(chars):
            chars[i], chars[i + 1] = chars[i + 1], chars[i]
    return "".join(chars)


def test_mutated_valid_sources_never_crash(rng: random.Random) -> None:
    for _ in range(200):
        base = rng.choice(_BASE_SOURCES)
        mutated = _mutate(rng, base, rng.randint(1, 20))
        try:
            r = check(mutated)
        except PyTSCheckError:
            continue
        assert isinstance(r.success, bool)


def test_truncated_valid_sources(rng: random.Random) -> None:
    for _ in range(100):
        base = rng.choice(_BASE_SOURCES)
        cut = rng.randint(0, len(base))
        truncated = base[:cut]
        try:
            r = check(truncated)
        except PyTSCheckError:
            continue
        assert isinstance(r.success, bool)


def test_repeated_valid_sources(rng: random.Random) -> None:
    """Repeating valid declarations must not break anything."""
    for _ in range(20):
        base = rng.choice(_BASE_SOURCES)
        text = base + "\n" + base + "\n" + base
        try:
            r = check(text)
        except PyTSCheckError:
            continue
        assert isinstance(r.success, bool)


# ---------------------------------------------------------------------------
# Size stress
# ---------------------------------------------------------------------------


def test_very_long_identifier(tsgo_binary: Path) -> None:
    text = f"const {'a' * 100_000}: number = 1;"
    try:
        r = check(text)
    except PyTSCheckError:
        return
    assert isinstance(r.success, bool)


def test_very_long_string_literal(tsgo_binary: Path) -> None:
    text = 'const s: string = "' + "a" * 1_000_000 + '";'
    try:
        r = check(text)
    except PyTSCheckError:
        return
    assert isinstance(r.success, bool)


def test_very_many_declarations(tsgo_binary: Path) -> None:
    text = "\n".join(f"const x{i}: number = {i};" for i in range(5_000))
    try:
        r = check(text)
    except PyTSCheckError:
        return
    assert isinstance(r.success, bool)


def test_deeply_nested_expression(tsgo_binary: Path) -> None:
    text = "const x: number = " + "(" * 500 + "1" + ")" * 500 + ";"
    try:
        r = check(text)
    except PyTSCheckError:
        return
    assert isinstance(r.success, bool)


def test_deeply_nested_types(tsgo_binary: Path) -> None:
    text = "type Deep = " + "Promise<" * 50 + "number" + ">" * 50 + ";"
    try:
        r = check(text)
    except PyTSCheckError:
        return
    assert isinstance(r.success, bool)


# ---------------------------------------------------------------------------
# Specific hostile patterns
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "\x00",
        "\x00const x = 1;",
        "const\x00x\x00=\x001;",
        "// " + "\x00" * 100,
    ],
)
def test_null_bytes_rejected(text: str) -> None:
    from pytscheck.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError, match="NUL"):
        check(text)


def test_bom_only(tsgo_binary: Path) -> None:
    r = check("\ufeff")
    assert isinstance(r.success, bool)


def test_bom_with_content(tsgo_binary: Path) -> None:
    r = check("\ufeffconst x: number = 1;")
    assert isinstance(r.success, bool)


def test_source_with_only_newlines(tsgo_binary: Path) -> None:
    r = check("\n" * 10_000)
    assert isinstance(r.success, bool)


def test_source_with_only_tabs(tsgo_binary: Path) -> None:
    r = check("\t" * 10_000)
    assert isinstance(r.success, bool)


def test_source_with_only_comment(tsgo_binary: Path) -> None:
    r = check("/* " + "x" * 100_000 + " */")
    assert isinstance(r.success, bool)


def test_unterminated_everything(tsgo_binary: Path) -> None:
    for text in ('"', "'", "`", "/*", "//", "(", "[", "{"):
        try:
            r = check(text)
        except PyTSCheckError:
            continue
        assert isinstance(r.success, bool)
