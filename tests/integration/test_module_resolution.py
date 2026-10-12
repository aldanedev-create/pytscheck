"""Integration tests for module resolution."""

from __future__ import annotations

from pathlib import Path

from pytscheck import check_project


def _setup(root: Path, tsconfig: str, files: dict[str, str]) -> Path:
    (root / "tsconfig.json").write_text(tsconfig, encoding="utf-8")
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


_STRICT_TSCONFIG = '{"compilerOptions": {"strict": true, "noEmit": true}, "include": ["**/*.ts"]}'


def test_relative_import(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        _STRICT_TSCONFIG,
        {
            "util.ts": "export const x: number = 1;\n",
            "main.ts": "import { x } from './util';\nexport const y: number = x;\n",
        },
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]


def test_relative_import_missing(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        _STRICT_TSCONFIG,
        {"main.ts": "import { x } from './nonexistent';\nexport const y = x;\n"},
    )
    r = check_project(tmp_path)
    assert not r.success


def test_index_file_resolution(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        _STRICT_TSCONFIG,
        {
            "lib/index.ts": "export const x: number = 1;\n",
            "main.ts": "import { x } from './lib';\nexport const y: number = x;\n",
        },
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]


def test_parent_directory_import(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        _STRICT_TSCONFIG,
        {
            "shared/util.ts": "export const shared: number = 1;\n",
            "src/main.ts": (
                "import { shared } from '../shared/util';\nexport const y: number = shared;\n"
            ),
        },
    )
    r = check_project(tmp_path)
    assert r.success


def test_path_alias(tsgo_binary, tsconfig_paths_alias: Path, tmp_path: Path) -> None:
    (tmp_path / "consumer.ts").write_text(
        "import { double } from '@lib/math';\nexport const y: number = double(3);\n",
        encoding="utf-8",
    )
    r = check_project(tmp_path)
    assert r.success, [d.message for d in r.errors]


def test_type_only_import(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        _STRICT_TSCONFIG,
        {
            "types.ts": "export interface User { name: string; }\n",
            "main.ts": (
                "import type { User } from './types';\nexport const u: User = { name: 'a' };\n"
            ),
        },
    )
    r = check_project(tmp_path)
    assert r.success


def test_circular_imports(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        _STRICT_TSCONFIG,
        {
            "a.ts": (
                "import { b } from './b';\nexport const a = 1;\nexport const combined = b + a;\n"
            ),
            "b.ts": (
                "import { a } from './a';\nexport const b = 2;\nexport const combined = a + b;\n"
            ),
        },
    )
    r = check_project(tmp_path)
    assert r.success


def test_namespace_import(tsgo_binary, tmp_path: Path) -> None:
    _setup(
        tmp_path,
        _STRICT_TSCONFIG,
        {
            "lib.ts": "export const a = 1;\nexport const b = 2;\n",
            "main.ts": "import * as lib from './lib';\nexport const sum: number = lib.a + lib.b;\n",
        },
    )
    r = check_project(tmp_path)
    assert r.success
