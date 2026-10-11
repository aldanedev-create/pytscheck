"""Integration tests against realistic TypeScript patterns."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import check_project


_STRICT = (
    '{"compilerOptions": {"strict": true, "noEmit": true, '
    '"target": "es2022", "module": "esnext", "moduleResolution": "bundler", '
    '"skipLibCheck": true, "esModuleInterop": true}, '
    '"include": ["**/*.ts"]}'
)


def _setup(root: Path, files: dict[str, str]) -> Path:
    (root / "tsconfig.json").write_text(_STRICT, encoding="utf-8")
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


def test_react_style_component(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        {
            "types.ts": (
                "export interface Props { name: string; onClick: () => void; }\n"
            ),
            "Button.ts": (
                "import type { Props } from './types';\n"
                "export function Button(props: Props): string {\n"
                "  return props.name;\n"
                "}\n"
            ),
        },
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]


def test_async_await_chain(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        {
            "main.ts": (
                "async function fetchData(): Promise<number> { return 42; }\n"
                "export async function main(): Promise<void> {\n"
                "  const n = await fetchData();\n"
                "  console.log(n);\n"
                "}\n"
            ),
        },
    )
    r = check_project(tmp_path)
    assert r.success


def test_generic_data_structures(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        {
            "stack.ts": (
                "export class Stack<T> {\n"
                "  private items: T[] = [];\n"
                "  push(item: T): void { this.items.push(item); }\n"
                "  pop(): T | undefined { return this.items.pop(); }\n"
                "}\n"
            ),
            "main.ts": (
                "import { Stack } from './stack';\n"
                "const s = new Stack<number>();\n"
                "s.push(1);\n"
                "export const n: number | undefined = s.pop();\n"
            ),
        },
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]


def test_discriminated_union(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        {
            "main.ts": (
                "type Shape =\n"
                "  | { kind: 'circle'; radius: number }\n"
                "  | { kind: 'square'; side: number };\n"
                "export function area(s: Shape): number {\n"
                "  switch (s.kind) {\n"
                "    case 'circle': return Math.PI * s.radius ** 2;\n"
                "    case 'square': return s.side ** 2;\n"
                "  }\n"
                "}\n"
            ),
        },
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]


def test_discriminated_union_exhaustiveness_error(
    tsgo_binary, tmp_path: Path
) -> None:
    _setup(
        tmp_path,
        {
            "main.ts": (
                "type Shape = { kind: 'circle' } | { kind: 'square' };\n"
                "export function f(s: Shape): string {\n"
                "  switch (s.kind) {\n"
                "    case 'circle': return 'c';\n"
                "  }\n"
                "}\n"
            ),
        },
    )
    r = check_project(tmp_path)
    # Under strict, missing return case is an error
    assert not r.success


def test_zod_style_validation_pattern(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        {
            "main.ts": (
                "type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };\n"
                "export function parse(s: string): Result<number, string> {\n"
                "  const n = Number(s);\n"
                "  if (Number.isNaN(n)) return { ok: false, error: 'bad' };\n"
                "  return { ok: true, value: n };\n"
                "}\n"
            ),
        },
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]


def test_recursive_types(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        {
            "tree.ts": (
                "export interface TreeNode {\n"
                "  value: number;\n"
                "  children: TreeNode[];\n"
                "}\n"
                "export function sum(n: TreeNode): number {\n"
                "  return n.value + n.children.reduce((acc, c) => acc + sum(c), 0);\n"
                "}\n"
            ),
        },
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]


def test_decorator_free_class_hierarchy(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        {
            "shapes.ts": (
                "export abstract class Shape {\n"
                "  abstract area(): number;\n"
                "}\n"
                "export class Circle extends Shape {\n"
                "  constructor(private r: number) { super(); }\n"
                "  area(): number { return Math.PI * this.r ** 2; }\n"
                "}\n"
            ),
        },
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]


def test_multi_module_app(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        {
            "models/user.ts": "export interface User { id: number; name: string; }\n",
            "services/api.ts": (
                "import type { User } from '../models/user';\n"
                "export async function fetchUser(id: number): Promise<User> {\n"
                "  return { id, name: 'a' };\n"
                "}\n"
            ),
            "app.ts": (
                "import { fetchUser } from './services/api';\n"
                "export async function main(): Promise<void> {\n"
                "  const u = await fetchUser(1);\n"
                "  console.log(u.name);\n"
                "}\n"
            ),
        },
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]


def test_commonjs_style(tsgo_binary, tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true, "module": "commonjs", '
        '"esModuleInterop": true}, "include": ["**/*.ts"]}',
        encoding="utf-8",
    )
    (tmp_path / "main.ts").write_text(
        "export = { hello: 'world' };\n", encoding="utf-8"
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]