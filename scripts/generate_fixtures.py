#!/usr/bin/env python3
"""Generate pytscheck's tests/fixtures/ tree from a declarative spec.

Run once by a contributor to (re)create the fixture files:

    python scripts/generate_fixtures.py

The generated .ts files are committed to the repository. This script is
NOT run during tests; it exists purely to make fixture maintenance
practical.

Design rules:

- Every fixture is defined in this file as a small, readable dict.
- The generator is idempotent: running it twice produces the same output.
- Files not owned by this generator are never touched.
- A manifest records what was generated so `verify_fixtures.py` can
  detect drift.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures"
MANIFEST_PATH = FIXTURES_ROOT / "MANIFEST.json"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Fixture:
    """One .ts (or .json, or .d.ts) fixture file."""

    relpath: str
    """Path relative to FIXTURES_ROOT, e.g. 'typescript/valid/const-number.ts'."""

    content: str
    """Full file content, including any header comment."""

    expect: str = "pass"
    """One of 'pass', 'fail', or 'either'. Used by tests to know what to assert."""

    codes: tuple[int, ...] = ()
    """If expect == 'fail', the expected TS error codes (may be empty)."""

    note: str = ""
    """Optional human note; also written as a header comment if `content` has none."""

    generated: bool = True
    """Whether this file is owned by this generator (True) or hand-authored (False)."""


@dataclass
class FixtureSet:
    """A named group of fixtures, used for reporting and manifest entries."""

    name: str
    fixtures: list[Fixture] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Header helper
# ---------------------------------------------------------------------------


def ts_file(
    body: str,
    *,
    expect: str = "pass",
    codes: tuple[int, ...] = (),
    note: str = "",
) -> str:
    """Wrap a TypeScript body with a standard header comment.

    The header documents what the fixture is for and, if applicable, what
    error code the test expects. It is a real comment, so the checker
    ignores it.
    """
    lines: list[str] = []
    if expect == "fail" and codes:
        codes_str = ", ".join(f"TS{c}" for c in codes)
        lines.append(f"// Expect: {codes_str}")
    elif expect == "fail":
        lines.append("// Expect: type error")
    if note:
        lines.append(f"// {note}")
    if lines:
        lines.append("")
    return "\n".join(lines) + body + ("\n" if not body.endswith("\n") else "")


# ---------------------------------------------------------------------------
# Fixture declarations
# ---------------------------------------------------------------------------


def fixtures_typescript_valid() -> list[Fixture]:
    base = "typescript/valid"
    return [
        Fixture(
            relpath=f"{base}/const-number.ts",
            content=ts_file("export const x: number = 1;"),
            note="minimal valid numeric constant",
        ),
        Fixture(
            relpath=f"{base}/const-string.ts",
            content=ts_file('export const s: string = "hello";'),
            note="minimal valid string constant",
        ),
        Fixture(
            relpath=f"{base}/function-basic.ts",
            content=ts_file(
                "export function add(a: number, b: number): number {\n"
                "  return a + b;\n"
                "}\n"
            ),
            note="typed function declaration",
        ),
        Fixture(
            relpath=f"{base}/interface-basic.ts",
            content=ts_file(
                "export interface User {\n"
                "  name: string;\n"
                "  age: number;\n"
                "}\n"
                "export const u: User = { name: 'a', age: 1 };\n"
            ),
            note="interface declaration and usage",
        ),
        Fixture(
            relpath=f"{base}/class-basic.ts",
            content=ts_file(
                "export class Point {\n"
                "  constructor(public x: number, public y: number) {}\n"
                "}\n"
            ),
            note="class with parameter properties",
        ),
        Fixture(
            relpath=f"{base}/type-alias-basic.ts",
            content=ts_file(
                "export type Pair = readonly [number, string];\n"
                "export const p: Pair = [1, 'a'] as const;\n"
            ),
            note="generic-free type alias",
        ),
        Fixture(
            relpath=f"{base}/empty.ts",
            content="",
            note="empty file is valid TypeScript",
        ),
        Fixture(
            relpath=f"{base}/comment-only.ts",
            content="// just a comment\n",
            note="comment-only file is valid",
        ),
        Fixture(
            relpath=f"{base}/unicode-content.ts",
            content=ts_file('export const s: string = "héllo 世界 🌍";'),
            note="Unicode string literal",
        ),
        Fixture(
            relpath=f"{base}/export-default.ts",
            content=ts_file(
                "export default function main(): void {}\n"
            ),
            note="export default function",
        ),
    ]


def fixtures_typescript_invalid() -> list[Fixture]:
    base = "typescript/invalid"
    return [
        Fixture(
            relpath=f"{base}/TS2322-type-mismatch-number.ts",
            content=ts_file(
                'export const x: number = "not a number";',
                expect="fail",
                codes=(2322,),
            ),
            expect="fail",
            codes=(2322,),
        ),
        Fixture(
            relpath=f"{base}/TS2322-type-mismatch-string.ts",
            content=ts_file(
                "export const s: string = 42;",
                expect="fail",
                codes=(2322,),
            ),
            expect="fail",
            codes=(2322,),
        ),
        Fixture(
            relpath=f"{base}/TS1005-missing-semicolon.ts",
            content=ts_file(
                "export const x: number = ",
                expect="fail",
                codes=(1005,),
            ),
            expect="fail",
            codes=(1005,),
        ),
        Fixture(
            relpath=f"{base}/TS2304-undefined-identifier.ts",
            content=ts_file(
                "console.log(notDefined);\n",
                expect="fail",
                codes=(2304, 2582, 2591),
            ),
            expect="fail",
            codes=(2304, 2582, 2591),
        ),
        Fixture(
            relpath=f"{base}/TS2554-wrong-arg-count.ts",
            content=ts_file(
                "function f(a: number, b: number): void {}\n"
                "f(1);\n",
                expect="fail",
                codes=(2554,),
            ),
            expect="fail",
            codes=(2554,),
        ),
        Fixture(
            relpath=f"{base}/TS2741-missing-property.ts",
            content=ts_file(
                "interface U { name: string; age: number; }\n"
                "export const u: U = { name: 'a' };\n",
                expect="fail",
                codes=(2741,),
            ),
            expect="fail",
            codes=(2741,),
        ),
        Fixture(
            relpath=f"{base}/TS2322-null-to-string.ts",
            content=ts_file(
                "export const s: string = null;",
                expect="fail",
                codes=(2322,),
            ),
            expect="fail",
            codes=(2322,),
        ),
        Fixture(
            relpath=f"{base}/TS1005-unterminated-string.ts",
            content='export const s: string = "unterminated\n',
            expect="fail",
            codes=(1002, 1005),
        ),
        Fixture(
            relpath=f"{base}/TS1005-unterminated-comment.ts",
            content="/* never closed\n",
            expect="fail",
            codes=(1010,),
        ),
        Fixture(
            relpath=f"{base}/TS1109-unexpected-token.ts",
            content="export const x: number = ;\n",
            expect="fail",
            codes=(1109, 1005),
        ),
    ]


# ---------------------------------------------------------------------------
# Feature-category fixtures
# ---------------------------------------------------------------------------


def fixtures_generics() -> list[Fixture]:
    base = "typescript/generics"
    return [
        Fixture(
            relpath=f"{base}/function-identity.ts",
            content=ts_file(
                "export function identity<T>(x: T): T { return x; }\n"
            ),
            note="basic generic function",
        ),
        Fixture(
            relpath=f"{base}/class-stack.ts",
            content=ts_file(
                "export class Stack<T> {\n"
                "  private items: T[] = [];\n"
                "  push(item: T): void { this.items.push(item); }\n"
                "  pop(): T | undefined { return this.items.pop(); }\n"
                "}\n"
            ),
            note="generic class",
        ),
        Fixture(
            relpath=f"{base}/constraint.ts",
            content=ts_file(
                "export function first<T extends { length: number }>(x: T): number {\n"
                "  return x.length;\n"
                "}\n"
            ),
            note="generic with constraint",
        ),
        Fixture(
            relpath=f"{base}/default-type-param.ts",
            content=ts_file(
                "export interface Wrapper<T = string> { value: T; }\n"
                "export const w: Wrapper = { value: 'a' };\n"
            ),
            note="generic with default type parameter",
        ),
        Fixture(
            relpath=f"{base}/TS2322-error-return.ts",
            content=ts_file(
                "export function identity<T>(x: T): T { return 'wrong'; }\n",
                expect="fail",
                codes=(2322,),
            ),
            expect="fail",
            codes=(2322,),
        ),
        Fixture(
            relpath=f"{base}/TS2344-error-constraint.ts",
            content=ts_file(
                "export function first<T extends { length: number }>(x: T) {}\n"
                "first(42);\n",
                expect="fail",
                codes=(2345, 2344),
            ),
            expect="fail",
            codes=(2345, 2344),
        ),
    ]


def fixtures_narrowing() -> list[Fixture]:
    base = "typescript/narrowing"
    return [
        Fixture(
            relpath=f"{base}/typeof.ts",
            content=ts_file(
                "export function f(x: string | number): string {\n"
                "  if (typeof x === 'string') { return x.toUpperCase(); }\n"
                "  return String(x);\n"
                "}\n"
            ),
            note="typeof narrowing",
        ),
        Fixture(
            relpath=f"{base}/instanceof.ts",
            content=ts_file(
                "export function f(e: unknown): string {\n"
                "  if (e instanceof Error) { return e.message; }\n"
                "  return String(e);\n"
                "}\n"
            ),
            note="instanceof narrowing",
        ),
        Fixture(
            relpath=f"{base}/in-operator.ts",
            content=ts_file(
                "export function f(o: { a: number } | { b: string }): number {\n"
                "  if ('a' in o) { return o.a; }\n"
                "  return o.b.length;\n"
                "}\n"
            ),
            note="in-operator narrowing",
        ),
        Fixture(
            relpath=f"{base}/discriminated-union.ts",
            content=ts_file(
                "type Shape =\n"
                "  | { kind: 'circle'; radius: number }\n"
                "  | { kind: 'square'; side: number };\n"
                "export function area(s: Shape): number {\n"
                "  if (s.kind === 'circle') return Math.PI * s.radius ** 2;\n"
                "  return s.side ** 2;\n"
                "}\n"
            ),
            note="discriminated union narrowing",
        ),
        Fixture(
            relpath=f"{base}/equality-narrowing.ts",
            content=ts_file(
                "export function f(x: string | null): string {\n"
                "  if (x === null) return '';\n"
                "  return x;\n"
                "}\n"
            ),
            note="null check narrowing",
        ),
        Fixture(
            relpath=f"{base}/TS18047-error-not-narrowed.ts",
            content=ts_file(
                "export function f(x: string | null): number {\n"
                "  return x.length;\n"
                "}\n",
                expect="fail",
                codes=(18047, 2531),
            ),
            expect="fail",
            codes=(18047, 2531),
        ),
    ]


def fixtures_unions() -> list[Fixture]:
    base = "typescript/unions"
    return [
        Fixture(
            relpath=f"{base}/basic.ts",
            content=ts_file(
                "export type T = 'a' | 'b' | 'c';\n"
                "export const t: T = 'b';\n"
            ),
            note="basic literal union",
        ),
        Fixture(
            relpath=f"{base}/with-primitives.ts",
            content=ts_file(
                "export function f(x: string | number | boolean): string {\n"
                "  return String(x);\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/TS2322-error.ts",
            content=ts_file(
                "export type T = 'a' | 'b';\n"
                "export const t: T = 'z';\n",
                expect="fail",
                codes=(2322,),
            ),
            expect="fail",
            codes=(2322,),
        ),
        Fixture(
            relpath=f"{base}/narrowed-access.ts",
            content=ts_file(
                "export function f(x: { a: number } | { b: string }): string {\n"
                "  if ('a' in x) return String(x.a);\n"
                "  return x.b;\n"
                "}\n"
            ),
        ),
    ]


def fixtures_intersections() -> list[Fixture]:
    base = "typescript/intersections"
    return [
        Fixture(
            relpath=f"{base}/basic.ts",
            content=ts_file(
                "type A = { a: number };\n"
                "type B = { b: string };\n"
                "export const x: A & B = { a: 1, b: 'x' };\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/function-composition.ts",
            content=ts_file(
                "export function compose<A, B, C>(f: (b: B) => C, g: (a: A) => B) {\n"
                "  return (a: A): C => f(g(a));\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/TS2322-error-missing-part.ts",
            content=ts_file(
                "type A = { a: number };\n"
                "type B = { b: string };\n"
                "export const x: A & B = { a: 1 };\n",
                expect="fail",
                codes=(2739,),
            ),
            expect="fail",
            codes=(2739,),
        ),
        Fixture(
            relpath=f"{base}/merged-interface.ts",
            content=ts_file(
                "interface A { a: number; }\n"
                "interface B { b: string; }\n"
                "export const x: A & B = { a: 1, b: 'x' };\n"
            ),
        ),
    ]


def fixtures_conditional_types() -> list[Fixture]:
    base = "typescript/conditional-types"
    return [
        Fixture(
            relpath=f"{base}/basic.ts",
            content=ts_file(
                "export type IsString<T> = T extends string ? true : false;\n"
                "export const a: IsString<'x'> = true;\n"
                "export const b: IsString<number> = false;\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/infer.ts",
            content=ts_file(
                "export type ElementType<T> = T extends (infer U)[] ? U : never;\n"
                "export const e: ElementType<number[]> = 1;\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/distributive.ts",
            content=ts_file(
                "export type Boxed<T> = T extends any ? { value: T } : never;\n"
                "export const b: Boxed<string | number> = { value: 'a' };\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/TS2322-error.ts",
            content=ts_file(
                "export type IsString<T> = T extends string ? true : false;\n"
                "export const a: IsString<'x'> = false;\n",
                expect="fail",
                codes=(2322,),
            ),
            expect="fail",
            codes=(2322,),
        ),
    ]


def fixtures_mapped_types() -> list[Fixture]:
    base = "typescript/mapped-types"
    return [
        Fixture(
            relpath=f"{base}/readonly.ts",
            content=ts_file(
                "export type Readonly<T> = { readonly [K in keyof T]: T[K] };\n"
                "interface U { a: number; b: string; }\n"
                "export const r: Readonly<U> = { a: 1, b: 'x' };\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/optional.ts",
            content=ts_file(
                "export type Partial<T> = { [K in keyof T]?: T[K] };\n"
                "interface U { a: number; }\n"
                "export const p: Partial<U> = {};\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/key-remapping.ts",
            content=ts_file(
                "export type Getters<T> = { [K in keyof T as `get${string & K}`]: () => T[K] };\n"
                "interface U { a: number; }\n"
                "export const g: Getters<U> = { geta: () => 1 };\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/TS2322-error-readonly.ts",
            content=ts_file(
                "export type Readonly<T> = { readonly [K in keyof T]: T[K] };\n"
                "interface U { a: number; }\n"
                "export const r: Readonly<U> = { a: 1 };\n"
                "r.a = 2;\n",
                expect="fail",
                codes=(2540,),
            ),
            expect="fail",
            codes=(2540,),
        ),
    ]


def fixtures_template_literal_types() -> list[Fixture]:
    base = "typescript/template-literal-types"
    return [
        Fixture(
            relpath=f"{base}/basic.ts",
            content=ts_file(
                "export type Greeting = `hello ${string}`;\n"
                "export const g: Greeting = 'hello world';\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/union-expansion.ts",
            content=ts_file(
                "export type Event = 'click' | 'hover';\n"
                "export type Handler = `on${Capitalize<Event>}`;\n"
                "export const h: Handler = 'onClick';\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/TS2322-error.ts",
            content=ts_file(
                "export type Greeting = `hello ${string}`;\n"
                "export const g: Greeting = 'goodbye';\n",
                expect="fail",
                codes=(2322,),
            ),
            expect="fail",
            codes=(2322,),
        ),
        Fixture(
            relpath=f"{base}/intrinsic-uppercase.ts",
            content=ts_file(
                "export type Loud = Uppercase<'hello'>;\n"
                "export const l: Loud = 'HELLO';\n"
            ),
        ),
    ]


def fixtures_overloads() -> list[Fixture]:
    base = "typescript/overloads"
    return [
        Fixture(
            relpath=f"{base}/basic.ts",
            content=ts_file(
                "export function f(x: string): string;\n"
                "export function f(x: number): number;\n"
                "export function f(x: string | number): string | number { return x; }\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/constructor.ts",
            content=ts_file(
                "export class Box {\n"
                "  constructor(x: string);\n"
                "  constructor(x: number);\n"
                "  constructor(public x: string | number) {}\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/TS2769-error-no-overload.ts",
            content=ts_file(
                "export function f(x: string): string;\n"
                "export function f(x: string): string { return x; }\n"
                "f(42);\n",
                expect="fail",
                codes=(2769,),
            ),
            expect="fail",
            codes=(2769,),
        ),
        Fixture(
            relpath=f"{base}/optional-param.ts",
            content=ts_file(
                "export function f(x: string): string;\n"
                "export function f(x: string, y?: number): string;\n"
                "export function f(x: string, y?: number): string { return x + (y ?? 0); }\n"
            ),
        ),
    ]


def fixtures_classes() -> list[Fixture]:
    base = "typescript/classes"
    return [
        Fixture(
            relpath=f"{base}/basic.ts",
            content=ts_file(
                "export class Point {\n"
                "  constructor(public x: number, public y: number) {}\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/inheritance.ts",
            content=ts_file(
                "export class Animal { name: string = 'x'; }\n"
                "export class Dog extends Animal { bark(): void {} }\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/abstract.ts",
            content=ts_file(
                "export abstract class Shape { abstract area(): number; }\n"
                "export class Circle extends Shape {\n"
                "  constructor(private r: number) { super(); }\n"
                "  area(): number { return Math.PI * this.r ** 2; }\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/implements.ts",
            content=ts_file(
                "export interface Serializable { serialize(): string; }\n"
                "export class Obj implements Serializable {\n"
                "  serialize(): string { return ''; }\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/private-field.ts",
            content=ts_file(
                "export class C { private value = 1; getValue(): number { return this.value; } }\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/TS2322-error-return.ts",
            content=ts_file(
                "export class C { method(): string { return 42; } }\n",
                expect="fail",
                codes=(2322,),
            ),
            expect="fail",
            codes=(2322,),
        ),
    ]


def fixtures_interfaces() -> list[Fixture]:
    base = "typescript/interfaces"
    return [
        Fixture(
            relpath=f"{base}/basic.ts",
            content=ts_file(
                "export interface User { name: string; age: number; }\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/optional.ts",
            content=ts_file(
                "export interface User { name: string; age?: number; }\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/extends.ts",
            content=ts_file(
                "export interface A { a: number; }\n"
                "export interface B extends A { b: string; }\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/TS2322-error-missing.ts",
            content=ts_file(
                "export interface User { name: string; }\n"
                "export const u: User = {};\n",
                expect="fail",
                codes=(2741,),
            ),
            expect="fail",
            codes=(2741,),
        ),
    ]


def fixtures_enums() -> list[Fixture]:
    base = "typescript/enums"
    return [
        Fixture(
            relpath=f"{base}/numeric.ts",
            content=ts_file(
                "export enum Color { Red, Green, Blue }\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/string.ts",
            content=ts_file(
                'export enum Level { Low = "low", High = "high" }\n'
            ),
        ),
        Fixture(
            relpath=f"{base}/const-enum.ts",
            content=ts_file(
                "export const enum Direction { Up, Down }\n"
                "export const d: Direction = Direction.Up;\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/TS2322-error.ts",
            content=ts_file(
                "export enum Color { Red, Green }\n"
                "export const c: Color = 'red';\n",
                expect="fail",
                codes=(2322,),
            ),
            expect="fail",
            codes=(2322,),
        ),
    ]


def fixtures_namespaces() -> list[Fixture]:
    base = "typescript/namespaces"
    return [
        Fixture(
            relpath=f"{base}/basic.ts",
            content=ts_file(
                "export namespace Math2 {\n"
                "  export function double(n: number): number { return n * 2; }\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/nested.ts",
            content=ts_file(
                "export namespace Outer {\n"
                "  export namespace Inner {\n"
                "    export const x: number = 1;\n"
                "  }\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/usage.ts",
            content=ts_file(
                "namespace N { export const x: number = 1; }\n"
                "export const y: number = N.x;\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/TS2339-error.ts",
            content=ts_file(
                "namespace N { export const x: number = 1; }\n"
                "export const y = N.notDefined;\n",
                expect="fail",
                codes=(2339,),
            ),
            expect="fail",
            codes=(2339,),
        ),
    ]


def fixtures_modules() -> list[Fixture]:
    base = "typescript/modules"
    return [
        Fixture(
            relpath=f"{base}/named-export.ts",
            content=ts_file(
                "export const a: number = 1;\n"
                "export const b: string = 'x';\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/default-export.ts",
            content=ts_file(
                "const value: number = 1;\n"
                "export default value;\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/reexport.ts",
            content=ts_file(
                "export { a } from './named-export';\n"
            ),
            note="re-export pattern; may need a resolution context",
        ),
        Fixture(
            relpath=f"{base}/namespace-import.ts",
            content=ts_file(
                "export const x: number = 1;\n"
                "export const y: number = 2;\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/type-only-export.ts",
            content=ts_file(
                "export interface User { name: string; }\n"
                "export type Alias = User;\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/side-effect-import.ts",
            content=ts_file(
                "// Side-effect import.\n"
                "export {};\n"
            ),
        ),
    ]


def fixtures_async() -> list[Fixture]:
    base = "typescript/async"
    return [
        Fixture(
            relpath=f"{base}/async-function.ts",
            content=ts_file(
                "export async function f(): Promise<number> { return 1; }\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/await.ts",
            content=ts_file(
                "async function get(): Promise<number> { return 1; }\n"
                "export async function main(): Promise<void> {\n"
                "  const n = await get();\n"
                "  console.log(n);\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/promise-chain.ts",
            content=ts_file(
                "export function f(): Promise<number> {\n"
                "  return Promise.resolve(1).then((x) => x + 1);\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/async-arrow.ts",
            content=ts_file(
                "export const f = async (): Promise<number> => 1;\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/TS2322-error-return-type.ts",
            content=ts_file(
                "export async function f(): Promise<number> { return 'wrong'; }\n",
                expect="fail",
                codes=(2322,),
            ),
            expect="fail",
            codes=(2322,),
        ),
        Fixture(
            relpath=f"{base}/for-await.ts",
            content=ts_file(
                "export async function f(xs: AsyncIterable<number>): Promise<void> {\n"
                "  for await (const x of xs) { console.log(x); }\n"
                "}\n"
            ),
        ),
    ]


def fixtures_decorators() -> list[Fixture]:
    base = "typescript/decorators"
    return [
        Fixture(
            relpath=f"{base}/method-decorator.ts",
            content=ts_file(
                "function log(target: object, key: string, desc: PropertyDescriptor): void {}\n"
                "export class C { @log method(): void {} }\n"
            ),
            note="method decorator (may require experimentalDecorators)",
        ),
        Fixture(
            relpath=f"{base}/class-decorator.ts",
            content=ts_file(
                "function sealed(target: Function): void {}\n"
                "@sealed\n"
                "export class C {}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/property-decorator.ts",
            content=ts_file(
                "function inject(target: object, key: string): void {}\n"
                "export class C { @inject value: number = 1; }\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/no-decorators.ts",
            content=ts_file(
                "export class C { method(): void {} }\n"
            ),
            note="control: same shape without decorators",
        ),
    ]


def fixtures_jsx() -> list[Fixture]:
    base = "typescript/jsx"
    return [
        Fixture(
            relpath=f"{base}/element.tsx",
            content=ts_file(
                "export const el = <div>Hello</div>;\n"
            ),
            note="basic JSX element",
        ),
        Fixture(
            relpath=f"{base}/props.tsx",
            content=ts_file(
                "interface Props { name: string; }\n"
                "export function Greet(props: Props) { return <span>{props.name}</span>; }\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/fragment.tsx",
            content=ts_file(
                "export const el = <><span>a</span><span>b</span></>;\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/conditional.tsx",
            content=ts_file(
                "export function F(props: { show: boolean }) {\n"
                "  return <div>{props.show ? <span>yes</span> : null}</div>;\n"
                "}\n"
            ),
        ),
    ]


def fixtures_tsx() -> list[Fixture]:
    base = "typescript/tsx"
    return [
        Fixture(
            relpath=f"{base}/component.tsx",
            content=ts_file(
                "type Props = { title: string };\n"
                "export function Component({ title }: Props) {\n"
                "  return <h1>{title}</h1>;\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/list.tsx",
            content=ts_file(
                "export function List({ items }: { items: string[] }) {\n"
                "  return <ul>{items.map((i) => <li key={i}>{i}</li>)}</ul>;\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/generic-component.tsx",
            content=ts_file(
                "export function Box<T>(props: { value: T }) {\n"
                "  return <div>{String(props.value)}</div>;\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/error-unknown-component.tsx",
            content=ts_file(
                "export const el = <UnknownComponent />;\n",
                expect="fail",
                codes=(2304, 2339, 7026),
            ),
            expect="fail",
            codes=(2304, 2339, 7026),
        ),
    ]


def fixtures_declaration_files() -> list[Fixture]:
    base = "typescript/declaration-files"
    return [
        Fixture(
            relpath=f"{base}/global.d.ts",
            content=ts_file(
                "declare const VERSION: string;\n"
                "declare function greet(name: string): string;\n"
            ),
            note="ambient global declarations",
        ),
        Fixture(
            relpath=f"{base}/module.d.ts",
            content=ts_file(
                "declare module 'vendor' {\n"
                "  export function parse(s: string): number;\n"
                "}\n"
            ),
            note="ambient module declaration",
        ),
        Fixture(
            relpath=f"{base}/types-only.d.ts",
            content=ts_file(
                "export interface User { name: string; }\n"
                "export type ID = number;\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/augment.d.ts",
            content=ts_file(
                "declare global {\n"
                "  interface Window { custom: string; }\n"
                "}\n"
                "export {};\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/consumer.ts",
            content=ts_file(
                "export const s: string = VERSION;\n"
            ),
            note="consumes global.d.ts",
        ),
        Fixture(
            relpath=f"{base}/no-implicit-any.d.ts",
            content=ts_file(
                "declare function f(x: string): string;\n"
            ),
        ),
    ]


def fixtures_strict_mode() -> list[Fixture]:
    base = "typescript/strict-mode"
    return [
        Fixture(
            relpath=f"{base}/null-checked.ts",
            content=ts_file(
                "export function f(x: string | null): number {\n"
                "  if (x === null) return 0;\n"
                "  return x.length;\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/undefined-checked.ts",
            content=ts_file(
                "export function f(x: string | undefined): string {\n"
                "  return x ?? '';\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/no-implicit-any-ok.ts",
            content=ts_file(
                "export function f(x: number): number { return x; }\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/strict-null-checks.ts",
            content=ts_file(
                "export function f(x: string | null): string {\n"
                "  return x;\n"
                "}\n",
                expect="fail",
                codes=(2322,),
            ),
            expect="fail",
            codes=(2322,),
        ),
        Fixture(
            relpath=f"{base}/implicit-any-error.ts",
            content=ts_file(
                "export function f(x) { return x; }\n",
                expect="fail",
                codes=(7006,),
            ),
            expect="fail",
            codes=(7006,),
        ),
        Fixture(
            relpath=f"{base}/strict-property-init.ts",
            content=ts_file(
                "export class C { value: number; }\n",
                expect="fail",
                codes=(2564,),
            ),
            expect="fail",
            codes=(2564,),
        ),
    ]


def fixtures_nullability() -> list[Fixture]:
    base = "typescript/nullability"
    return [
        Fixture(
            relpath=f"{base}/optional-chain.ts",
            content=ts_file(
                "export function f(x: { a?: { b?: number } }): number {\n"
                "  return x.a?.b ?? 0;\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/nullish-coalesce.ts",
            content=ts_file(
                "export const x: number = null ?? 1;\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/non-null-assertion.ts",
            content=ts_file(
                "export function f(x: string | null): number {\n"
                "  return x!.length;\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/undefined-union.ts",
            content=ts_file(
                "export function f(x?: string): string {\n"
                "  return x ?? '';\n"
                "}\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/TS2531-error-object-null.ts",
            content=ts_file(
                "export function f(x: string | null): number {\n"
                "  return x.length;\n"
                "}\n",
                expect="fail",
                codes=(18047, 2531),
            ),
            expect="fail",
            codes=(18047, 2531),
        ),
        Fixture(
            relpath=f"{base}/TS2532-error-object-undefined.ts",
            content=ts_file(
                "export function f(x?: string): number {\n"
                "  return x.length;\n"
                "}\n",
                expect="fail",
                codes=(18048, 2532),
            ),
            expect="fail",
            codes=(18048, 2532),
        ),
    ]


def fixtures_inference() -> list[Fixture]:
    base = "typescript/inference"
    return [
        Fixture(
            relpath=f"{base}/literal-inference.ts",
            content=ts_file(
                "export const x = 1;\n"
                "export const s = 'a';\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/array-inference.ts",
            content=ts_file(
                "export const arr = [1, 2, 3];\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/object-inference.ts",
            content=ts_file(
                "export const obj = { a: 1, b: 'x' };\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/return-inference.ts",
            content=ts_file(
                "export function f() { return 42; }\n"
            ),
        ),
    ]


def fixtures_standard_library() -> list[Fixture]:
    base = "typescript/standard-library"
    return [
        Fixture(
            relpath=f"{base}/array.ts",
            content=ts_file(
                "export const arr: Array<number> = [1, 2, 3];\n"
                "export const doubled: number[] = arr.map((x) => x * 2);\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/map.ts",
            content=ts_file(
                "export const m: Map<string, number> = new Map();\n"
                "m.set('a', 1);\n"
                "export const v: number | undefined = m.get('a');\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/set.ts",
            content=ts_file(
                "export const s: Set<number> = new Set([1, 2, 3]);\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/promise.ts",
            content=ts_file(
                "export const p: Promise<number> = Promise.resolve(1);\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/json.ts",
            content=ts_file(
                "export const s: string = JSON.stringify({ a: 1 });\n"
                "export const o: unknown = JSON.parse('{}');\n"
            ),
        ),
        Fixture(
            relpath=f"{base}/regexp.ts",
            content=ts_file(
                "export const re: RegExp = /abc/g;\n"
                "export const m: RegExpMatchArray | null = 'abc'.match(re);\n"
            ),
        ),
    ]


def fixtures_regressions() -> list[Fixture]:
    base = "typescript/regressions"
    return [
        Fixture(
            relpath=f"{base}/README.md",
            content=(
                "# Regression fixtures\n"
                "\n"
                "Each file here corresponds to a bug that was found and fixed.\n"
                "Name files after the issue or PR that introduced the fix:\n"
                "\n"
                "    issue-123-multiline-message.ts\n"
                "    pr-456-path-with-parens.ts\n"
                "\n"
                "The header comment in each fixture names the bug.\n"
            ),
            generated=False,
        ),
    ]


# ---------------------------------------------------------------------------
# Project fixtures
# ---------------------------------------------------------------------------


def _project_readme(name: str, purpose: str) -> Fixture:
    return Fixture(
        relpath=f"projects/{name}/README.md",
        content=f"# {name}\n\n{purpose}\n",
        generated=False,
    )


def fixtures_projects_minimal() -> list[Fixture]:
    return [
        _project_readme(
            "minimal",
            "One tsconfig.json and one clean .ts file. Used by basic "
            "project-checking tests.",
        ),
        Fixture(
            relpath="projects/minimal/tsconfig.json",
            content=(
                "{\n"
                '  "compilerOptions": {\n'
                '    "strict": true,\n'
                '    "noEmit": true,\n'
                '    "target": "es2022",\n'
                '    "module": "esnext"\n'
                "  },\n"
                '  "include": ["**/*.ts"]\n'
                "}\n"
            ),
        ),
        Fixture(
            relpath="projects/minimal/main.ts",
            content="export const x: number = 1;\n",
        ),
    ]


def fixtures_projects_monorepo() -> list[Fixture]:
    return [
        _project_readme(
            "monorepo",
            "Two packages plus a root tsconfig. Used by project-references "
            "and workspace tests.",
        ),
        Fixture(
            relpath="projects/monorepo/tsconfig.json",
            content=(
                "{\n"
                '  "compilerOptions": {"strict": true, "noEmit": true},\n'
                '  "include": ["packages/**/*.ts"]\n'
                "}\n"
            ),
        ),
        Fixture(
            relpath="projects/monorepo/packages/a/package.json",
            content='{"name": "a", "version": "0.0.0"}\n',
        ),
        Fixture(
            relpath="projects/monorepo/packages/a/index.ts",
            content="export const a: number = 1;\n",
        ),
        Fixture(
            relpath="projects/monorepo/packages/b/package.json",
            content='{"name": "b", "version": "0.0.0"}\n',
        ),
        Fixture(
            relpath="projects/monorepo/packages/b/index.ts",
            content="export const b: string = 'b';\n",
        ),
    ]


def fixtures_projects_path_aliases() -> list[Fixture]:
    return [
        _project_readme(
            "path-aliases",
            "tsconfig.json with a `paths` mapping. Used by module-resolution tests.",
        ),
        Fixture(
            relpath="projects/path-aliases/tsconfig.json",
            content=(
                "{\n"
                '  "compilerOptions": {\n'
                '    "strict": true,\n'
                '    "noEmit": true,\n'
                '    "baseUrl": ".",\n'
                '    "paths": {"@lib/*": ["src/lib/*"]}\n'
                "  },\n"
                '  "include": ["**/*.ts"]\n'
                "}\n"
            ),
        ),
        Fixture(
            relpath="projects/path-aliases/src/lib/math.ts",
            content=(
                "export function double(n: number): number { return n * 2; }\n"
            ),
        ),
        Fixture(
            relpath="projects/path-aliases/src/main.ts",
            content=(
                "import { double } from '@lib/math';\n"
                "export const x: number = double(3);\n"
            ),
        ),
        Fixture(
            relpath="projects/path-aliases/src/broken.ts",
            content=(
                "import { notThere } from '@lib/missing';\n"
                "export const y = notThere;\n"
            ),
            expect="fail",
            codes=(2307,),
        ),
    ]


def fixtures_projects_references() -> list[Fixture]:
    return [
        _project_readme(
            "references",
            "Two projects where one references the other via `references`. "
            "Used by project-reference tests.",
        ),
        Fixture(
            relpath="projects/references/tsconfig.json",
            content=(
                "{\n"
                '  "compilerOptions": {"strict": true, "noEmit": true},\n'
                '  "include": ["lib/**/*.ts"],\n'
                '  "references": [{"path": "./app"}]\n'
                "}\n"
            ),
        ),
        Fixture(
            relpath="projects/references/lib/util.ts",
            content=(
                "export function double(n: number): number { return n * 2; }\n"
            ),
        ),
        Fixture(
            relpath="projects/references/app/tsconfig.json",
            content=(
                "{\n"
                '  "compilerOptions": {\n'
                '    "strict": true,\n'
                '    "noEmit": true,\n'
                '    "composite": true,\n'
                '    "outDir": "./dist"\n'
                "  },\n"
                '  "include": ["**/*.ts"]\n'
                "}\n"
            ),
        ),
        Fixture(
            relpath="projects/references/app/main.ts",
            content=(
                "import { double } from '../lib/util';\n"
                "export const x: number = double(3);\n"
            ),
        ),
        Fixture(
            relpath="projects/references/app/broken.ts",
            content=(
                "export const bad: number = 'string';\n"
            ),
            expect="fail",
            codes=(2322,),
        ),
    ]


def fixtures_projects_custom_types() -> list[Fixture]:
    return [
        _project_readme(
            "custom-types",
            "A hand-written .d.ts file plus a .ts file that consumes it. "
            "Used by declaration-file tests.",
        ),
        Fixture(
            relpath="projects/custom-types/tsconfig.json",
            content=(
                "{\n"
                '  "compilerOptions": {"strict": true, "noEmit": true},\n'
                '  "include": ["**/*.ts"]\n'
                "}\n"
            ),
        ),
        Fixture(
            relpath="projects/custom-types/types.d.ts",
            content=(
                "declare function greet(name: string): string;\n"
                "declare const VERSION: string;\n"
            ),
        ),
        Fixture(
            relpath="projects/custom-types/main.ts",
            content=(
                "export const s: string = greet(VERSION);\n"
            ),
        ),
    ]


def fixtures_projects_broken_config() -> list[Fixture]:
    return [
        _project_readme(
            "broken-config",
            "Intentionally invalid tsconfig.json. Used by config-error tests.",
        ),
        Fixture(
            relpath="projects/broken-config/tsconfig.json",
            content='{ "compilerOptions": { "strict": true\n',
            note="unterminated object; the loader must raise ConfigurationError",
        ),
        Fixture(
            relpath="projects/broken-config/main.ts",
            content="export const x: number = 1;\n",
        ),
    ]


# ---------------------------------------------------------------------------
# Registry of all fixture sets
# ---------------------------------------------------------------------------


FIXTURE_SETS: list[FixtureSet] = [
    FixtureSet("typescript/valid", fixtures_typescript_valid()),
    FixtureSet("typescript/invalid", fixtures_typescript_invalid()),
    FixtureSet("typescript/generics", fixtures_generics()),
    FixtureSet("typescript/narrowing", fixtures_narrowing()),
    FixtureSet("typescript/unions", fixtures_unions()),
    FixtureSet("typescript/intersections", fixtures_intersections()),
    FixtureSet("typescript/conditional-types", fixtures_conditional_types()),
    FixtureSet("typescript/mapped-types", fixtures_mapped_types()),
    FixtureSet(
        "typescript/template-literal-types", fixtures_template_literal_types()
    ),
    FixtureSet("typescript/overloads", fixtures_overloads()),
    FixtureSet("typescript/classes", fixtures_classes()),
    FixtureSet("typescript/interfaces", fixtures_interfaces()),
    FixtureSet("typescript/enums", fixtures_enums()),
    FixtureSet("typescript/namespaces", fixtures_namespaces()),
    FixtureSet("typescript/modules", fixtures_modules()),
    FixtureSet("typescript/async", fixtures_async()),
    FixtureSet("typescript/decorators", fixtures_decorators()),
    FixtureSet("typescript/jsx", fixtures_jsx()),
    FixtureSet("typescript/tsx", fixtures_tsx()),
    FixtureSet("typescript/declaration-files", fixtures_declaration_files()),
    FixtureSet("typescript/strict-mode", fixtures_strict_mode()),
    FixtureSet("typescript/nullability", fixtures_nullability()),
    FixtureSet("typescript/inference", fixtures_inference()),
    FixtureSet("typescript/standard-library", fixtures_standard_library()),
    FixtureSet("typescript/regressions", fixtures_regressions()),
    FixtureSet("projects/minimal", fixtures_projects_minimal()),
    FixtureSet("projects/monorepo", fixtures_projects_monorepo()),
    FixtureSet("projects/path-aliases", fixtures_projects_path_aliases()),
    FixtureSet("projects/references", fixtures_projects_references()),
    FixtureSet("projects/custom-types", fixtures_projects_custom_types()),
    FixtureSet("projects/broken-config", fixtures_projects_broken_config()),
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def all_fixtures() -> Iterable[Fixture]:
    for fs in FIXTURE_SETS:
        for f in fs.fixtures:
            yield f


def write_fixture(fixture: Fixture, *, force: bool) -> str:
    """Write one fixture. Returns 'created', 'updated', or 'skipped'."""
    path = FIXTURES_ROOT / fixture.relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        current = path.read_text(encoding="utf-8")
        if current == fixture.content:
            return "skipped"
        return "would-update"
    action = "updated" if path.exists() else "created"
    path.write_text(fixture.content, encoding="utf-8")
    return action


def build_manifest() -> dict:
    entries: list[dict] = []
    for fixture in all_fixtures():
        entry: dict = {
            "path": fixture.relpath,
            "expect": fixture.expect,
            "generated": fixture.generated,
        }
        if fixture.codes:
            entry["codes"] = list(fixture.codes)
        if fixture.note:
            entry["note"] = fixture.note
        entries.append(entry)
    return {
        "generator": "scripts/generate_fixtures.py",
        "version": 1,
        "fixture_count": len(entries),
        "fixtures": entries,
    }


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    force = "--force" in argv
    dry_run = "--dry-run" in argv
    write_manifest = "--manifest" in argv or dry_run

    counts = {"created": 0, "updated": 0, "skipped": 0, "would-update": 0}

    for fixture in all_fixtures():
        if dry_run:
            path = FIXTURES_ROOT / fixture.relpath
            if path.exists() and path.read_text(encoding="utf-8") != fixture.content:
                print(f"WOULD UPDATE {fixture.relpath}")
                counts["would-update"] += 1
            elif not path.exists():
                print(f"WOULD CREATE {fixture.relpath}")
                counts["created"] += 1
            else:
                counts["skipped"] += 1
            continue

        action = write_fixture(fixture, force=force)
        counts[action] += 1
        if action in {"created", "updated"}:
            print(f"{action.upper():8s} {fixture.relpath}")

    if write_manifest and not dry_run:
        manifest = build_manifest()
        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"manifest written: {MANIFEST_PATH}")

    print()
    print("Summary:")
    print(f"  created:      {counts['created']}")
    print(f"  updated:      {counts['updated']}")
    print(f"  skipped:      {counts['skipped']}")
    if dry_run:
        print(f"  would-update: {counts['would-update']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())