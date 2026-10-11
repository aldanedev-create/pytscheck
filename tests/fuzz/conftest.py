"""Fixtures for fuzz tests."""

from __future__ import annotations

import random

import pytest


@pytest.fixture
def rng() -> random.Random:
    """A deterministic RNG seeded per test.

    Hypothesis is used where shrinking matters. For parser fuzzing where
    we want to reason about specific byte classes, a seeded `random.Random`
    keeps failures reproducible.
    """
    return random.Random(0xC0FFEE)


@pytest.fixture
def printable_alphabet() -> str:
    """Printable ASCII, the alphabet the parser is expected to handle."""
    return "".join(chr(i) for i in range(0x20, 0x7F))


@pytest.fixture
def hostile_alphabet() -> str:
    """Bytes and control characters that the parser must survive."""
    return "".join(chr(i) for i in list(range(0x00, 0x20)) + [0x7F, 0x80, 0xFF])


@pytest.fixture
def typescript_snippets() -> list[str]:
    """Realistic TypeScript fragments for grammar-aware fuzzing."""
    return [
        "const x: number = 1;",
        "let s: string = 'a';",
        "function f(a: number, b: number): number { return a + b; }",
        "interface U { name: string; age: number; }",
        "type T = 'a' | 'b' | 'c';",
        "class C { constructor(public x: number) {} }",
        "export default function(): void {}",
        "export { x } from './mod';",
        "import type { U } from './types';",
        "const arr: Array<number> = [1, 2, 3];",
        "async function main(): Promise<void> {}",
        "enum E { A, B, C }",
        "namespace N { export const x = 1; }",
        "const g = <T,>(x: T): T => x;",
        "type Mapped<T> = { [K in keyof T]: T[K] };",
    ]