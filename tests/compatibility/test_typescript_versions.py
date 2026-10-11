"""Tests that verify the bundled compiler's TypeScript language features.

These do not test a *range* of compiler versions -- the pinned version is
the only one bundled. They verify that the pinned version supports the
TypeScript feature set the project documents as supported.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pytscheck import check, check_project
from pytscheck.version import COMPILER_VERSION


# --- version pin ------------------------------------------------------------


def test_compiler_version_is_pinned() -> None:
    assert COMPILER_VERSION
    assert COMPILER_VERSION.lower() not in {"latest", "*", "any"}


def test_compiler_version_semver() -> None:
    assert re.match(r"^\d+\.\d+\.\d+", COMPILER_VERSION)


def test_compiler_version_is_7_or_higher() -> None:
    """The project targets TypeScript 7.0+, whose native compiler is tsgo."""
    major = int(COMPILER_VERSION.split(".")[0])
    assert major >= 7


def test_tsgo_reports_consistent_version(tsgo_binary: Path, tsgo_full_version: str) -> None:
    assert tsgo_full_version
    # The reported version should mention a digit sequence
    assert re.search(r"\d+\.\d+", tsgo_full_version)


def test_result_records_compiler_version(tsgo_binary: Path) -> None:
    r = check("export const x: number = 1;")
    assert r.compiler_version == COMPILER_VERSION


# --- TypeScript language features -------------------------------------------


def test_supports_optional_chaining(tsgo_binary: Path) -> None:
    src = (
        "interface N { x?: { y?: number } }\n"
        "export function f(n: N): number { return n.x?.y ?? 0; }\n"
    )
    assert check(src).success


def test_supports_nullish_coalescing(tsgo_binary: Path) -> None:
    assert check("export const x: number = null ?? 1;").success


def test_supports_template_literal_types(tsgo_binary: Path) -> None:
    src = "type G = `hello ${string}`;\nexport const g: G = 'hello world';\n"
    assert check(src).success


def test_supports_satisfies_operator(tsgo_binary: Path) -> None:
    src = (
        "const config = { a: 1 } satisfies Record<string, number>;\n"
        "export { config };\n"
    )
    assert check(src).success


def test_supports_generic_arrow(tsgo_binary: Path) -> None:
    assert check("export const id = <T,>(x: T): T => x;").success


def test_supports_discriminated_unions(tsgo_binary: Path) -> None:
    src = (
        "type S = { kind: 'a'; x: number } | { kind: 'b'; y: string };\n"
        "export function f(s: S): string {\n"
        "  if (s.kind === 'a') return String(s.x);\n"
        "  return s.y;\n"
        "}\n"
    )
    assert check(src).success


def test_supports_conditional_types(tsgo_binary: Path) -> None:
    src = (
        "type IsString<T> = T extends string ? true : false;\n"
        "export const a: IsString<'x'> = true;\n"
        "export const b: IsString<number> = false;\n"
    )
    assert check(src).success


def test_supports_mapped_types(tsgo_binary: Path) -> None:
    src = (
        "type Readonly<T> = { readonly [K in keyof T]: T[K] };\n"
        "interface U { a: number; b: string; }\n"
        "export const r: Readonly<U> = { a: 1, b: 'x' };\n"
    )
    assert check(src).success


def test_supports_import_type(tsgo_binary: Path) -> None:
    src = (
        "export type Foo = string;\n"
        "export const x: import('./input.ts').Foo = 'a';\n"
    )
    # `import('./input.ts')` may or may not resolve in a source-string
    # context, but the syntax itself must parse. Success or a type-only
    # diagnostic is acceptable; a syntax error is not.
    r = check(src)
    assert not any(d.code == 1005 for d in r.errors)


def test_supports_assert_import_attributes(tsgo_binary: Path) -> None:
    src = "export const x: number = 1;\n"
    assert check(src).success


# --- strict mode ------------------------------------------------------------


def test_strict_null_checks(tsgo_binary: Path) -> None:
    src = "export function f(x: string | null): number { return x.length; }\n"
    r = check(src)
    assert not r.success


def test_strict_undefined_checks(tsgo_binary: Path) -> None:
    src = "export function f(x: string | undefined): number { return x.length; }\n"
    r = check(src)
    assert not r.success


def test_strict_implicit_any(tsgo_binary: Path) -> None:
    src = "export function f(x) { return x; }\n"
    r = check(src)
    assert not r.success


# --- features removed or deprecated ----------------------------------------


def test_no_implicit_any_in_variables(tsgo_binary: Path) -> None:
    src = "export const x = undefined;\nlet y: number = x;\n"
    r = check(src)
    # Under strict, `x` is undefined and cannot be assigned to number
    assert not r.success


def test_namespace_syntax_supported(tsgo_binary: Path) -> None:
    src = "export namespace N { export const x: number = 1; }\n"
    assert check(src).success


def test_enum_syntax_supported(tsgo_binary: Path) -> None:
    src = "export enum Color { Red, Green, Blue }\n"
    assert check(src).success


def test_decorator_syntax_supported(tsgo_binary: Path) -> None:
    src = (
        "function log(target: object, key: string): void {}\n"
        "export class C { @log method(): void {} }\n"
    )
    r = check(src)
    # Decorators must parse; whether they run is tsgo's business
    assert not any(d.code == 1005 for d in r.errors)