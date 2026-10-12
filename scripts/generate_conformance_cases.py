#!/usr/bin/env python3
"""Generate conformance/cases/ from a declarative spec.

Same pattern as scripts/generate_fixtures.py:

- cases are defined here as small readable dicts
- the generator is idempotent
- output is committed to git
- a companion verifier detects drift

The cases here are the *inputs* to the conformance runner. Their expected
outputs live in conformance/expected/ and are produced by
scripts/update_conformance.py after this script runs.

Usage:

    python scripts/generate_conformance_cases.py --dry-run
    python scripts/generate_conformance_cases.py --manifest
    python scripts/generate_conformance_cases.py --force --manifest
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CASES_ROOT = REPO_ROOT / "conformance" / "cases"
MANIFEST_PATH = REPO_ROOT / "conformance" / "manifest.json"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Case:
    """One conformance case file."""

    relpath: str
    """Path relative to CASES_ROOT, e.g. 'assignability/basic.ts'."""

    content: str
    """Full file content, including any header comment."""

    description: str = ""
    """One-line human summary. Written as a header comment if content has none."""

    category: str = ""
    """Implicit from relpath; kept for readability."""

    generated: bool = True
    """True if this file is owned by the generator."""


@dataclass
class CaseSet:
    name: str
    cases: list[Case] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def ts(body: str, *, description: str = "") -> str:
    """Wrap a TypeScript body with a standard header comment."""
    header: list[str] = []
    if description:
        header.append(f"// {description}")
    if header:
        header.append("")
    return "\n".join(header) + body + ("\n" if not body.endswith("\n") else "")


# ---------------------------------------------------------------------------
# Category declarations
# ---------------------------------------------------------------------------


def cases_assignability() -> list[Case]:
    base = "assignability"
    return [
        Case(
            relpath=f"{base}/literal-to-primitive.ts",
            content=ts(
                "const a: number = 1;\n"
                "const b: string = 'x';\n"
                "const c: boolean = true;\n"
                "export { a, b, c };\n",
                description="literals assignable to their primitives",
            ),
            description="literals assignable to their primitives",
        ),
        Case(
            relpath=f"{base}/literal-mismatch.ts",
            content=ts(
                'export const a: number = "string";\n',
                description="string literal to number: TS2322",
            ),
            description="string literal to number: TS2322",
        ),
        Case(
            relpath=f"{base}/structural-compat.ts",
            content=ts(
                "interface A { a: number; }\n"
                "interface B { a: number; b: string; }\n"
                "const a: A = { a: 1 };\n"
                "const b: B = { a: 1, b: 'x' };\n"
                "const aFromB: A = b;\n"
                "export { a, b, aFromB };\n",
                description="structural compatibility",
            ),
            description="structural compatibility",
        ),
        Case(
            relpath=f"{base}/missing-property.ts",
            content=ts(
                "interface A { a: number; b: string; }\nexport const x: A = { a: 1 };\n",
                description="missing property: TS2741",
            ),
            description="missing property: TS2741",
        ),
        Case(
            relpath=f"{base}/union-to-narrower.ts",
            content=ts(
                "export function f(x: string | number): string {\n  return x;\n}\n",
                description="union not assignable to member: TS2322",
            ),
            description="union not assignable to member: TS2322",
        ),
        Case(
            relpath=f"{base}/narrower-to-union.ts",
            content=ts(
                "export function f(x: string): string | number {\n  return x;\n}\n",
                description="member assignable to union",
            ),
            description="member assignable to union",
        ),
    ]


def cases_inference() -> list[Case]:
    base = "inference"
    return [
        Case(
            relpath=f"{base}/literal.ts",
            content=ts(
                "export const x = 1;\nexport const s = 'a';\n",
                description="literal inference",
            ),
            description="literal inference",
        ),
        Case(
            relpath=f"{base}/array.ts",
            content=ts(
                "export const arr = [1, 2, 3];\n",
                description="array element inference",
            ),
            description="array element inference",
        ),
        Case(
            relpath=f"{base}/object.ts",
            content=ts(
                "export const o = { a: 1, b: 'x' };\n",
                description="object literal inference",
            ),
            description="object literal inference",
        ),
        Case(
            relpath=f"{base}/return.ts",
            content=ts(
                "export function f() { return 42; }\n",
                description="return type inference",
            ),
            description="return type inference",
        ),
        Case(
            relpath=f"{base}/contextual.ts",
            content=ts(
                "export const xs: number[] = [1, 2, 3].map((x) => x * 2);\n",
                description="contextual parameter inference",
            ),
            description="contextual parameter inference",
        ),
        Case(
            relpath=f"{base}/implicit-any-param.ts",
            content=ts(
                "export function f(x) { return x; }\n",
                description="implicit any under strict: TS7006",
            ),
            description="implicit any under strict: TS7006",
        ),
    ]


def cases_generics() -> list[Case]:
    base = "generics"
    return [
        Case(
            relpath=f"{base}/identity.ts",
            content=ts(
                "export function id<T>(x: T): T { return x; }\n",
                description="identity function",
            ),
            description="identity function",
        ),
        Case(
            relpath=f"{base}/constraint.ts",
            content=ts(
                "export function first<T extends { length: number }>(x: T): number {\n"
                "  return x.length;\n"
                "}\n",
                description="constrained type parameter",
            ),
            description="constrained type parameter",
        ),
        Case(
            relpath=f"{base}/class-stack.ts",
            content=ts(
                "export class Stack<T> {\n"
                "  private items: T[] = [];\n"
                "  push(x: T): void { this.items.push(x); }\n"
                "  pop(): T | undefined { return this.items.pop(); }\n"
                "}\n",
                description="generic class",
            ),
            description="generic class",
        ),
        Case(
            relpath=f"{base}/default-param.ts",
            content=ts(
                "export interface Box<T = string> { value: T; }\n"
                "export const b: Box = { value: 'a' };\n",
                description="default type parameter",
            ),
            description="default type parameter",
        ),
        Case(
            relpath=f"{base}/wrong-return.ts",
            content=ts(
                "export function id<T>(x: T): T { return 'wrong'; }\n",
                description="generic return violation: TS2322",
            ),
            description="generic return violation: TS2322",
        ),
        Case(
            relpath=f"{base}/constraint-violation.ts",
            content=ts(
                "export function first<T extends { length: number }>(x: T) {}\nfirst(42);\n",
                description="constraint violation: TS2345",
            ),
            description="constraint violation: TS2345",
        ),
    ]


def cases_functions() -> list[Case]:
    base = "functions"
    return [
        Case(
            relpath=f"{base}/basic.ts",
            content=ts(
                "export function add(a: number, b: number): number {\n  return a + b;\n}\n",
                description="typed function",
            ),
            description="typed function",
        ),
        Case(
            relpath=f"{base}/optional-param.ts",
            content=ts(
                "export function greet(name: string, greeting?: string): string {\n"
                "  return (greeting ?? 'hi') + ', ' + name;\n"
                "}\n",
                description="optional parameter",
            ),
            description="optional parameter",
        ),
        Case(
            relpath=f"{base}/default-param.ts",
            content=ts(
                "export function greet(name: string, greeting = 'hi'): string {\n"
                "  return greeting + ', ' + name;\n"
                "}\n",
                description="default parameter value",
            ),
            description="default parameter value",
        ),
        Case(
            relpath=f"{base}/rest-param.ts",
            content=ts(
                "export function sum(...xs: number[]): number {\n"
                "  return xs.reduce((a, b) => a + b, 0);\n"
                "}\n",
                description="rest parameter",
            ),
            description="rest parameter",
        ),
        Case(
            relpath=f"{base}/wrong-arg-type.ts",
            content=ts(
                "export function add(a: number, b: number): number { return a + b; }\n"
                "add(1, 'two');\n",
                description="wrong argument type: TS2345",
            ),
            description="wrong argument type: TS2345",
        ),
        Case(
            relpath=f"{base}/missing-arg.ts",
            content=ts(
                "export function add(a: number, b: number): number { return a + b; }\nadd(1);\n",
                description="missing argument: TS2554",
            ),
            description="missing argument: TS2554",
        ),
    ]


def cases_classes() -> list[Case]:
    base = "classes"
    return [
        Case(
            relpath=f"{base}/basic.ts",
            content=ts(
                "export class Point {\n"
                "  constructor(public x: number, public y: number) {}\n"
                "  distance(): number { return Math.hypot(this.x, this.y); }\n"
                "}\n",
                description="basic class with parameter properties",
            ),
            description="basic class with parameter properties",
        ),
        Case(
            relpath=f"{base}/inheritance.ts",
            content=ts(
                "export class Animal { name: string = 'x'; }\n"
                "export class Dog extends Animal {\n"
                "  bark(): void {}\n"
                "}\n",
                description="class inheritance",
            ),
            description="class inheritance",
        ),
        Case(
            relpath=f"{base}/abstract.ts",
            content=ts(
                "export abstract class Shape {\n"
                "  abstract area(): number;\n"
                "}\n"
                "export class Circle extends Shape {\n"
                "  constructor(private r: number) { super(); }\n"
                "  area(): number { return Math.PI * this.r ** 2; }\n"
                "}\n",
                description="abstract class",
            ),
            description="abstract class",
        ),
        Case(
            relpath=f"{base}/implements.ts",
            content=ts(
                "export interface Serializable { serialize(): string; }\n"
                "export class Obj implements Serializable {\n"
                "  serialize(): string { return ''; }\n"
                "}\n",
                description="implements interface",
            ),
            description="implements interface",
        ),
        Case(
            relpath=f"{base}/wrong-return.ts",
            content=ts(
                "export class C { method(): string { return 42; } }\n",
                description="wrong return type in method: TS2322",
            ),
            description="wrong return type in method: TS2322",
        ),
        Case(
            relpath=f"{base}/abstract-not-implemented.ts",
            content=ts(
                "export abstract class Shape { abstract area(): number; }\n"
                "export class Square extends Shape {}\n",
                description="abstract member not implemented: TS2515",
            ),
            description="abstract member not implemented: TS2515",
        ),
    ]


def cases_unions() -> list[Case]:
    base = "unions"
    return [
        Case(
            relpath=f"{base}/literal.ts",
            content=ts(
                "export type T = 'a' | 'b' | 'c';\nexport const t: T = 'b';\n",
                description="literal union",
            ),
            description="literal union",
        ),
        Case(
            relpath=f"{base}/primitive.ts",
            content=ts(
                "export function f(x: string | number | boolean): string {\n"
                "  return String(x);\n"
                "}\n",
                description="primitive union",
            ),
            description="primitive union",
        ),
        Case(
            relpath=f"{base}/discriminated.ts",
            content=ts(
                "export type Shape =\n"
                "  | { kind: 'circle'; radius: number }\n"
                "  | { kind: 'square'; side: number };\n"
                "export function area(s: Shape): number {\n"
                "  if (s.kind === 'circle') return Math.PI * s.radius ** 2;\n"
                "  return s.side ** 2;\n"
                "}\n",
                description="discriminated union",
            ),
            description="discriminated union",
        ),
        Case(
            relpath=f"{base}/invalid-literal.ts",
            content=ts(
                "export type T = 'a' | 'b';\nexport const t: T = 'z';\n",
                description="literal not in union: TS2322",
            ),
            description="literal not in union: TS2322",
        ),
    ]


def cases_intersections() -> list[Case]:
    base = "intersections"
    return [
        Case(
            relpath=f"{base}/basic.ts",
            content=ts(
                "type A = { a: number };\n"
                "type B = { b: string };\n"
                "export const x: A & B = { a: 1, b: 'x' };\n",
                description="basic intersection",
            ),
            description="basic intersection",
        ),
        Case(
            relpath=f"{base}/function.ts",
            content=ts(
                "export function compose<A, B, C>(f: (b: B) => C, g: (a: A) => B) {\n"
                "  return (a: A): C => f(g(a));\n"
                "}\n",
                description="intersection with generics",
            ),
            description="intersection with generics",
        ),
        Case(
            relpath=f"{base}/missing-part.ts",
            content=ts(
                "type A = { a: number };\n"
                "type B = { b: string };\n"
                "export const x: A & B = { a: 1 };\n",
                description="missing intersection part: TS2739",
            ),
            description="missing intersection part: TS2739",
        ),
    ]


def cases_narrowing() -> list[Case]:
    base = "narrowing"
    return [
        Case(
            relpath=f"{base}/typeof.ts",
            content=ts(
                "export function f(x: string | number): string {\n"
                "  if (typeof x === 'string') return x.toUpperCase();\n"
                "  return String(x);\n"
                "}\n",
                description="typeof narrowing",
            ),
            description="typeof narrowing",
        ),
        Case(
            relpath=f"{base}/instanceof.ts",
            content=ts(
                "export function f(e: unknown): string {\n"
                "  if (e instanceof Error) return e.message;\n"
                "  return String(e);\n"
                "}\n",
                description="instanceof narrowing",
            ),
            description="instanceof narrowing",
        ),
        Case(
            relpath=f"{base}/in-operator.ts",
            content=ts(
                "export function f(o: { a: number } | { b: string }): number {\n"
                "  if ('a' in o) return o.a;\n"
                "  return o.b.length;\n"
                "}\n",
                description="in-operator narrowing",
            ),
            description="in-operator narrowing",
        ),
        Case(
            relpath=f"{base}/equality.ts",
            content=ts(
                "export function f(x: string | null): string {\n"
                "  if (x === null) return '';\n"
                "  return x;\n"
                "}\n",
                description="equality narrowing",
            ),
            description="equality narrowing",
        ),
        Case(
            relpath=f"{base}/discriminated.ts",
            content=ts(
                "type S = { k: 'a'; v: number } | { k: 'b'; v: string };\n"
                "export function f(s: S): string {\n"
                "  if (s.k === 'a') return String(s.v);\n"
                "  return s.v;\n"
                "}\n",
                description="discriminated union narrowing",
            ),
            description="discriminated union narrowing",
        ),
        Case(
            relpath=f"{base}/not-narrowed.ts",
            content=ts(
                "export function f(x: string | null): number {\n  return x.length;\n}\n",
                description="not narrowed: TS18047",
            ),
            description="not narrowed: TS18047",
        ),
    ]


def cases_nullability() -> list[Case]:
    base = "nullability"
    return [
        Case(
            relpath=f"{base}/optional-chain.ts",
            content=ts(
                "export function f(x: { a?: { b?: number } }): number {\n"
                "  return x.a?.b ?? 0;\n"
                "}\n",
                description="optional chaining",
            ),
            description="optional chaining",
        ),
        Case(
            relpath=f"{base}/nullish.ts",
            content=ts(
                "export const x: number = null ?? 1;\n",
                description="nullish coalescing",
            ),
            description="nullish coalescing",
        ),
        Case(
            relpath=f"{base}/non-null.ts",
            content=ts(
                "export function f(x: string | null): number {\n  return x!.length;\n}\n",
                description="non-null assertion",
            ),
            description="non-null assertion",
        ),
        Case(
            relpath=f"{base}/strict-null-error.ts",
            content=ts(
                "export function f(x: string | null): string {\n  return x;\n}\n",
                description="null to non-nullable: TS2322",
            ),
            description="null to non-nullable: TS2322",
        ),
        Case(
            relpath=f"{base}/possibly-null.ts",
            content=ts(
                "export function f(x: string | null): number {\n  return x.length;\n}\n",
                description="possibly null access: TS18047",
            ),
            description="possibly null access: TS18047",
        ),
        Case(
            relpath=f"{base}/optional-undefined.ts",
            content=ts(
                "export function f(x?: string): number {\n  return x.length;\n}\n",
                description="possibly undefined access: TS18048",
            ),
            description="possibly undefined access: TS18048",
        ),
    ]


def cases_modules() -> list[Case]:
    base = "modules"
    return [
        Case(
            relpath=f"{base}/named-exports.ts",
            content=ts(
                "export const a: number = 1;\nexport const b: string = 'x';\n",
                description="named exports",
            ),
            description="named exports",
        ),
        Case(
            relpath=f"{base}/default-export.ts",
            content=ts(
                "const value: number = 1;\nexport default value;\n",
                description="default export",
            ),
            description="default export",
        ),
        Case(
            relpath=f"{base}/type-only.ts",
            content=ts(
                "export interface User { name: string; }\nexport type Alias = User;\n",
                description="type-only exports",
            ),
            description="type-only exports",
        ),
        Case(
            relpath=f"{base}/reexport.ts",
            content=ts(
                "export { a } from './named-exports';\n",
                description="re-export",
            ),
            description="re-export",
        ),
        Case(
            relpath=f"{base}/star-export.ts",
            content=ts(
                "export * from './named-exports';\n",
                description="star export",
            ),
            description="star export",
        ),
        Case(
            relpath=f"{base}/ambient-module.ts",
            content=ts(
                "declare module 'vendor' {\n"
                "  export function parse(s: string): number;\n"
                "}\n"
                "export {};\n",
                description="ambient module declaration",
            ),
            description="ambient module declaration",
        ),
    ]


def cases_declarations() -> list[Case]:
    base = "declarations"
    return [
        Case(
            relpath=f"{base}/function.d.ts",
            content=ts(
                "declare function greet(name: string): string;\n",
                description="ambient function declaration",
            ),
            description="ambient function declaration",
        ),
        Case(
            relpath=f"{base}/const.d.ts",
            content=ts(
                "declare const VERSION: string;\n",
                description="ambient const declaration",
            ),
            description="ambient const declaration",
        ),
        Case(
            relpath=f"{base}/interface.d.ts",
            content=ts(
                "export interface User { name: string; age: number; }\n",
                description="exported interface",
            ),
            description="exported interface",
        ),
        Case(
            relpath=f"{base}/augment.d.ts",
            content=ts(
                "declare global {\n  interface Window { custom: string; }\n}\nexport {};\n",
                description="global augmentation",
            ),
            description="global augmentation",
        ),
    ]


def cases_compiler_options() -> list[Case]:
    base = "compiler-options"
    return [
        Case(
            relpath=f"{base}/strict-mode.ts",
            content=ts(
                "export function f(x: string | null): number {\n  return x.length;\n}\n",
                description="strict null checks enabled",
            ),
            description="strict null checks enabled",
        ),
        Case(
            relpath=f"{base}/no-implicit-any.ts",
            content=ts(
                "export function f(x) { return x; }\n",
                description="noImplicitAny enabled: TS7006",
            ),
            description="noImplicitAny enabled: TS7006",
        ),
        Case(
            relpath=f"{base}/non-strict.ts",
            content=ts(
                "export const x = undefined;\nexport const y: number = x;\n",
                description="relaxed typing context",
            ),
            description="relaxed typing context",
        ),
        Case(
            relpath=f"{base}/es2022-target.ts",
            content=ts(
                "export const x: number = 1;\n"
                "export class C { #private = 1; get(): number { return this.#private; } }\n",
                description="ES2022 target features",
            ),
            description="ES2022 target features",
        ),
    ]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


CASE_SETS: list[CaseSet] = [
    CaseSet("assignability", cases_assignability()),
    CaseSet("inference", cases_inference()),
    CaseSet("generics", cases_generics()),
    CaseSet("functions", cases_functions()),
    CaseSet("classes", cases_classes()),
    CaseSet("unions", cases_unions()),
    CaseSet("intersections", cases_intersections()),
    CaseSet("narrowing", cases_narrowing()),
    CaseSet("nullability", cases_nullability()),
    CaseSet("modules", cases_modules()),
    CaseSet("declarations", cases_declarations()),
    CaseSet("compiler-options", cases_compiler_options()),
]


def all_cases() -> Iterable[Case]:
    for cs in CASE_SETS:
        yield from cs.cases


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------


def build_manifest() -> dict:
    cases = list(all_cases())
    categories: dict[str, int] = {}
    entries: list[dict] = []
    for case in cases:
        category = Path(case.relpath).parts[0] if "/" in case.relpath else "root"
        categories[category] = categories.get(category, 0) + 1
        entry: dict = {
            "path": case.relpath,
            "description": case.description,
            "generated": case.generated,
        }
        entries.append(entry)
    return {
        "generator": "scripts/generate_conformance_cases.py",
        "version": 1,
        "case_count": len(entries),
        "categories": dict(sorted(categories.items())),
        "cases": entries,
    }


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def write_case(case: Case, *, force: bool) -> str:
    path = CASES_ROOT / case.relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        current = path.read_text(encoding="utf-8")
        if current == case.content:
            return "skipped"
        return "would-update"
    action = "updated" if path.exists() else "created"
    path.write_text(case.content, encoding="utf-8")
    return action


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_conformance_cases",
        description="Generate conformance/cases/ from a declarative spec.",
    )
    parser.add_argument("--force", action="store_true", help="overwrite hand-edited case files")
    parser.add_argument(
        "--dry-run", action="store_true", help="report what would change, write nothing"
    )
    parser.add_argument(
        "--manifest", action="store_true", help="write/update conformance/manifest.json"
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    counts = {"created": 0, "updated": 0, "skipped": 0, "would-update": 0}
    changes: list[str] = []

    for case in all_cases():
        if args.dry_run:
            path = CASES_ROOT / case.relpath
            if path.exists() and path.read_text(encoding="utf-8") != case.content:
                changes.append(f"WOULD UPDATE {case.relpath}")
                counts["would-update"] += 1
            elif not path.exists():
                changes.append(f"WOULD CREATE {case.relpath}")
                counts["created"] += 1
            else:
                counts["skipped"] += 1
            continue

        action = write_case(case, force=args.force)
        counts[action] += 1
        if action in {"created", "updated"}:
            changes.append(f"{action.upper():8s} {case.relpath}")

    if args.manifest and not args.dry_run:
        manifest = build_manifest()
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        changes.append(f"wrote {MANIFEST_PATH.relative_to(REPO_ROOT)}")

    if args.json:
        print(
            json.dumps(
                {
                    "changes": changes,
                    "counts": counts,
                },
                indent=2,
            )
        )
    else:
        for line in changes:
            print(line)
        print()
        print("Summary:")
        print(f"  created:      {counts['created']}")
        print(f"  updated:      {counts['updated']}")
        print(f"  skipped:      {counts['skipped']}")
        if args.dry_run:
            print(f"  would-update: {counts['would-update']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
