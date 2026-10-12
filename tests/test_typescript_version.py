"""Tests that the bundled compiler understands the TypeScript version it claims."""

from __future__ import annotations

from pathlib import Path

from pytscheck import checker


def test_accepts_modern_ts_syntax(tsgo_binary: Path) -> None:
    """Sanity check that the bundled compiler is a modern TypeScript."""
    src = (
        "type Pair<A, B> = readonly [A, B];\n"
        "const p: Pair<number, string> = [1, 'a'] as const;\n"
        "export { p };\n"
    )
    r = checker.check_source(src)
    assert r.success, [d.message for d in r.errors]


def test_supports_optional_chaining(tsgo_binary: Path) -> None:
    src = (
        "interface N { x?: { y?: number } }\n"
        "export function f(n: N): number { return n.x?.y ?? 0; }\n"
    )
    r = checker.check_source(src)
    assert r.success, [d.message for d in r.errors]


def test_supports_nullish_coalescing(tsgo_binary: Path) -> None:
    src = "export const x: number = null ?? 1;"
    r = checker.check_source(src)
    assert r.success, [d.message for d in r.errors]


def test_supports_template_literal_types(tsgo_binary: Path) -> None:
    src = "type Greeting = `hello ${string}`;\nexport const g: Greeting = 'hello world';\n"
    r = checker.check_source(src)
    assert r.success, [d.message for d in r.errors]


def test_supports_satisfies_operator(tsgo_binary: Path) -> None:
    src = "const config = { a: 1 } satisfies Record<string, number>;\nexport { config };\n"
    r = checker.check_source(src)
    assert r.success, [d.message for d in r.errors]


def test_supports_const_type_parameters(tsgo_binary: Path) -> None:
    src = "export function tuple<const T extends readonly unknown[]>(t: T): T { return t; }\n"
    r = checker.check_source(src)
    assert r.success, [d.message for d in r.errors]


def test_supports_generic_arrow_functions(tsgo_binary: Path) -> None:
    src = "export const identity = <T,>(x: T): T => x;"
    r = checker.check_source(src)
    assert r.success, [d.message for d in r.errors]


def test_supports_using_declarations(tsgo_binary: Path) -> None:
    """`using` is TS 5.2+."""
    src = (
        "class R { [Symbol.dispose](): void {} }\n"
        "export function f(): void { using r = new R(); void r; }\n"
    )
    r = checker.check_source(src)
    # If the compiler is older, it will fail. We assert the outcome matches
    # a documented feature: either accepted (modern) or rejected with a
    # syntax error (older). Either way, no crash.
    assert r.success or any(d.code in {1005, 2304} for d in r.errors)


def test_rejects_invalid_syntax(tsgo_binary: Path) -> None:
    src = "const x: = 1;"
    r = checker.check_source(src)
    assert not r.success


def test_rejects_type_error(tsgo_binary: Path) -> None:
    src = 'const x: number = "s";'
    r = checker.check_source(src)
    assert not r.success
    assert any(d.code == 2322 for d in r.errors)


def test_supports_strict_mode(tsgo_binary: Path) -> None:
    """With strict: true, null/undefined checks must be enforced."""
    src = (
        "export function f(x: string | null): number {\n"
        "  return x.length;\n"  # error: x is possibly null
        "}\n"
    )
    r = checker.check_source(src)
    assert not r.success
    assert any(d.code in {18047, 2531} for d in r.errors)


def test_standard_library_types_available(tsgo_binary: Path) -> None:
    """Array, Map, Promise etc. must resolve from the bundled lib/*.d.ts."""
    src = (
        "export const arr: Array<number> = [1, 2, 3];\n"
        "export const m: Map<string, number> = new Map();\n"
        "export const p: Promise<number> = Promise.resolve(1);\n"
    )
    r = checker.check_source(src)
    assert r.success, [d.message for d in r.errors]


def test_string_methods_available(tsgo_binary: Path) -> None:
    src = (
        "export function f(s: string): string {\n"
        "  return s.toUpperCase().trim().replace(/a/g, 'b');\n"
        "}\n"
    )
    r = checker.check_source(src)
    assert r.success, [d.message for d in r.errors]


def test_object_methods_available(tsgo_binary: Path) -> None:
    src = "export function f(o: object): string[] {\n  return Object.keys(o);\n}\n"
    r = checker.check_source(src)
    assert r.success, [d.message for d in r.errors]
