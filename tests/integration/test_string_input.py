"""Integration tests for checking in-memory source strings."""

from __future__ import annotations

import pytest

from pytscheck import check
from tests.assertions import (
    assert_has_error_code,
    assert_no_diagnostics,
    assert_valid_result,
)


def test_empty_string_is_valid(tsgo_binary) -> None:
    r = check("")
    assert_valid_result(r)
    assert r.success


def test_whitespace_only_is_valid(tsgo_binary) -> None:
    r = check("   \n\t\n")
    assert_valid_result(r)
    assert r.success


def test_comment_only_is_valid(tsgo_binary) -> None:
    r = check("// just a comment\n")
    assert_valid_result(r)
    assert r.success


def test_simple_declaration(tsgo_binary) -> None:
    r = check("const x: number = 1;")
    assert_valid_result(r)
    assert r.success


def test_exported_declaration(tsgo_binary) -> None:
    r = check("export const answer: number = 42;")
    assert r.success


def test_function_declaration(tsgo_binary) -> None:
    r = check("function add(a: number, b: number): number { return a + b; }")
    assert r.success


def test_class_declaration(tsgo_binary) -> None:
    r = check("class Point { constructor(public x: number) {} }")
    assert r.success


def test_interface_declaration(tsgo_binary) -> None:
    r = check("interface User { name: string; age: number; }")
    assert r.success


def test_type_alias(tsgo_binary) -> None:
    r = check("type Pair<A, B> = readonly [A, B];")
    assert r.success


def test_generic_function(tsgo_binary) -> None:
    r = check("function identity<T>(x: T): T { return x; }")
    assert r.success


def test_type_error_number_from_string(tsgo_binary) -> None:
    r = check('const age: number = "twenty";')
    assert_valid_result(r)
    assert not r.success
    assert_has_error_code(r, 2322)


def test_type_error_string_from_number(tsgo_binary) -> None:
    r = check("const s: string = 42;")
    assert not r.success
    assert_has_error_code(r, 2322)


def test_type_error_undefined_identifier(tsgo_binary) -> None:
    r = check("console.log(notDefined);")
    assert not r.success
    assert any(d.code in {2304, 2582, 2591} for d in r.errors)


def test_type_error_wrong_argument_count(tsgo_binary) -> None:
    r = check(
        "function f(a: number, b: number): void {} "
        "f(1);"
    )
    assert not r.success
    assert any(d.code in {2554, 2555} for d in r.errors)


def test_type_error_missing_property(tsgo_binary) -> None:
    r = check(
        "interface User { name: string; } "
        "const u: User = { name: 'a', extra: 1 };"
    )
    assert not r.success
    assert any(d.code in {2353, 2322} for d in r.errors)


def test_syntax_error(tsgo_binary) -> None:
    r = check("const x: number = ;")
    assert not r.success
    assert_has_error_code(r, 1005)


def test_syntax_error_unclosed_brace(tsgo_binary) -> None:
    r = check("function f() { ")
    assert not r.success
    assert any(d.code in {1005, 1109, 1128} for d in r.errors)


def test_custom_filename(tsgo_binary) -> None:
    r = check('const age: number = "twenty";', filename="custom.ts")
    assert not r.success
    assert any(d.file == "custom.ts" for d in r.errors)


def test_keep_raw(tsgo_binary) -> None:
    r = check('const age: number = "twenty";', keep_raw=True)
    assert r.raw_output is not None
    assert r.raw_output.strip()


def test_no_keep_raw_by_default(tsgo_binary) -> None:
    r = check("const x = 1;")
    assert r.raw_output is None


def test_elapsed_seconds_positive(tsgo_binary) -> None:
    r = check("const x = 1;")
    assert r.elapsed_seconds > 0.0


def test_compiler_version_recorded(tsgo_binary) -> None:
    r = check("const x = 1;")
    assert r.compiler_version


def test_repeated_checks_produce_identical_results(tsgo_binary) -> None:
    src = 'const age: number = "twenty";'
    results = [check(src) for _ in range(3)]
    first = results[0]
    for r in results[1:]:
        assert r.success == first.success
        assert r.diagnostics == first.diagnostics


def test_no_diagnostics_means_success(tsgo_binary) -> None:
    r = check("export const x: number = 1;")
    assert_no_diagnostics(r)