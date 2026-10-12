"""Real project/compiler integration for framework-independent adapters."""

from __future__ import annotations

import json
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from pytscheck import SourceFile, check_project
from pytscheck.adapters import DeclarationResource, ProjectContext
from pytscheck.exceptions import AdapterProtocolError, ConfigurationError


class Adapter:
    name = "context-example"

    def __init__(self, sources: list[SourceFile], context: ProjectContext | None = None) -> None:
        self.sources = sources
        self.context = context or ProjectContext()

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return self.sources

    def get_context(self, project_root: str) -> ProjectContext:
        return self.context


def config(root: Path, options: dict) -> None:
    (root / "tsconfig.json").write_text(
        json.dumps({"compilerOptions": options, "include": ["src/**/*"]})
    )


def test_generated_real_and_alias_imports(tsgo_binary: Path, tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "value.ts").write_text("export const value: number = 1;")
    (src / "consumer.ts").write_text("import { answer } from './generated'; export { answer };")
    config(
        tmp_path,
        {"module": "preserve", "moduleResolution": "bundler", "paths": {"@/*": ["./src/*"]}},
    )
    adapter = Adapter(
        [
            SourceFile(
                "src/generated.ts",
                "import { value } from '@/value'; import { other } from './other'; "
                "export const answer: number = value + other;",
            ),
            SourceFile("src/other.ts", "export const other: number = 2;"),
        ]
    )
    assert check_project(tmp_path, adapter=adapter).success
    assert not (src / "generated.ts").exists()
    assert not list(tmp_path.glob(".pytscheck-*"))


def test_inherits_strict_false_and_partial_override(tsgo_binary: Path, tmp_path: Path) -> None:
    config(tmp_path, {"strict": False})
    adapter = Adapter([SourceFile("src/generated.ts", "export function value(x) { return x; }")])
    assert check_project(tmp_path, adapter=adapter, options={"target": "es2022"}).success
    result = check_project(tmp_path, adapter=adapter, options={"strict": True})
    assert any(d.code == 7006 for d in result.errors)


def test_parent_config_alias_origin(tsgo_binary: Path, tmp_path: Path) -> None:
    shared = tmp_path / "base.json"
    shared.write_text(
        json.dumps(
            {
                "compilerOptions": {
                    "strict": False,
                    "paths": {"@/*": ["./app/src/*"]},
                    "moduleResolution": "bundler",
                    "module": "preserve",
                }
            }
        )
    )
    root = tmp_path / "app"
    (root / "src").mkdir(parents=True)
    (root / "src/value.ts").write_text("export const value = 1;")
    (root / "tsconfig.json").write_text('{"extends":"../base.json","include":["src/*.ts"]}')
    adapter = Adapter(
        [SourceFile("src/generated.ts", "import { value } from '@/value'; export { value };")]
    )
    assert check_project(root, adapter=adapter).success


def test_installed_node_declarations_are_found(tsgo_binary: Path, tmp_path: Path) -> None:
    package = tmp_path / "node_modules" / "sample-package"
    package.mkdir(parents=True)
    (package / "package.json").write_text('{"name":"sample-package","types":"index.d.ts"}')
    (package / "index.d.ts").write_text("export declare const value: number;")
    adapter = Adapter(
        [
            SourceFile(
                "src/generated.ts",
                "import { value } from 'sample-package'; export const answer: number = value;",
            )
        ]
    )
    assert check_project(tmp_path, adapter=adapter).success


def test_pypi_resource_declarations_without_node_modules(
    tsgo_binary: Path, tmp_path: Path, monkeypatch
) -> None:
    installed = tmp_path / "installed"
    package = installed / "context_example_types"
    (package / "types").mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "types/index.d.ts").write_text("export declare const value: number;")
    archive = tmp_path / "declarations.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        for path in package.rglob("*"):
            if path.is_file():
                bundle.write(path, path.relative_to(installed))
    monkeypatch.syspath_prepend(str(archive))
    root = tmp_path / "app"
    root.mkdir()
    context = ProjectContext(
        declaration_resources=(
            DeclarationResource("context_example_types", module="sample-package"),
        )
    )
    adapter = Adapter(
        [
            SourceFile(
                "generated.ts",
                "import { value } from 'sample-package'; export const answer: number = value;",
            )
        ],
        context,
    )
    assert check_project(root, adapter=adapter).success
    assert not (root / "node_modules").exists()


def test_filesystem_ambient_declarations(tsgo_binary: Path, tmp_path: Path) -> None:
    declarations = tmp_path / "types.d.ts"
    declarations.write_text('declare module "virtual-library" { export const value: number; }')
    context = ProjectContext(declaration_paths=(declarations,))
    adapter = Adapter(
        [SourceFile("generated.ts", "import { value } from 'virtual-library'; export { value };")],
        context,
    )
    assert check_project(tmp_path, adapter=adapter).success


def test_real_file_collision_never_overwrites(tsgo_binary: Path, tmp_path: Path) -> None:
    real = tmp_path / "app.ts"
    real.write_text("original contents")
    with pytest.raises(AdapterProtocolError, match="conflicts"):
        check_project(tmp_path, adapter=Adapter([SourceFile("app.ts", "export const value = 1;")]))
    assert real.read_text() == "original contents"
    assert not list(tmp_path.glob(".pytscheck-*"))


def test_cleanup_after_errors_and_workspace_limit(tsgo_binary: Path, tmp_path: Path) -> None:
    result = check_project(
        tmp_path, adapter=Adapter([SourceFile("app.ts", 'export const value: number = "bad";')])
    )
    assert any(d.code == 2322 for d in result.errors)
    with pytest.raises(ConfigurationError, match="limit"):
        check_project(
            tmp_path,
            adapter=Adapter(
                [SourceFile("app.ts", "export const value = 1;")],
                ProjectContext(max_workspace_bytes=1),
            ),
        )
    assert not list(tmp_path.glob(".pytscheck-*"))


def test_concurrent_workspaces_are_isolated(tsgo_binary: Path, tmp_path: Path) -> None:
    adapter = Adapter([SourceFile("app.ts", "export const value = 1;")])
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert all(pool.map(lambda _: check_project(tmp_path, adapter=adapter).success, range(4)))
    assert not list(tmp_path.glob(".pytscheck-*"))


def test_jsx_and_emitting_config_are_checked_without_outputs(
    tsgo_binary: Path, tmp_path: Path
) -> None:
    config(tmp_path, {"jsx": "preserve", "noEmit": False, "strict": False})
    context = ProjectContext(declaration_paths=(tmp_path / "jsx.d.ts",))
    (tmp_path / "jsx.d.ts").write_text(
        "declare namespace JSX { interface IntrinsicElements { button: { count: number }; } }"
    )
    adapter = Adapter(
        [SourceFile("src/generated.tsx", "export const view = <button count={1} />;")], context
    )
    assert check_project(tmp_path, adapter=adapter).success
    assert not list(tmp_path.rglob("*.jsx"))
    assert not list(tmp_path.glob(".pytscheck-*"))


def test_broad_include_does_not_capture_snapshot(tsgo_binary: Path, tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text('{"include":["**/*.ts"]}')
    (tmp_path / "real.ts").write_text("export const value = 1;")
    adapter = Adapter(
        [SourceFile("generated.ts", "import { value } from './real'; export { value };")]
    )
    assert check_project(tmp_path, adapter=adapter).success


def test_jsdoc_context_uses_project_checkjs(tsgo_binary: Path, tmp_path: Path) -> None:
    config(tmp_path, {"allowJs": True, "checkJs": True})
    adapter = Adapter(
        [SourceFile("src/generated.js", '/** @type {number} */\nexport const value = "bad";')]
    )
    result = check_project(tmp_path, adapter=adapter)
    assert any(d.code == 2322 for d in result.errors)


def test_workspace_cleanup_on_real_timeout(tsgo_binary: Path, tmp_path: Path) -> None:
    from pytscheck.checker import _use_runner
    from pytscheck.exceptions import CompilerTimeoutError
    from pytscheck.runner import run

    def short(args, *, cwd=None):
        return run(args, cwd=cwd, timeout=0.000001)

    adapter = Adapter([SourceFile("generated.ts", "export const value = 1;")])
    with _use_runner(short), pytest.raises(CompilerTimeoutError):
        check_project(tmp_path, adapter=adapter)
    assert not list(tmp_path.glob(".pytscheck-*"))
