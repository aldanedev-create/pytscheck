"""Framework-independent component and schema consumers of ProjectContext."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pytscheck import SourceFile, check_project
from pytscheck.adapters import ProjectContext


class ComponentTool:
    name = "component-example"

    def get_context(self, project_root: str) -> ProjectContext:
        return ProjectContext()

    def get_sources(self, project_root: str) -> list[SourceFile]:
        # A consuming compiler provides both generated text and token mappings.
        return [
            SourceFile(
                "src/Widget.generated.ts",
                'export const count: number = "wrong";',
                origin_path="src/Widget.component",
                source_map=json.dumps(
                    {"version": 3, "sources": ["Widget.component"], "mappings": "aAIa"}
                ),
            )
        ]


class SchemaTool:
    name = "schema-example"

    def get_context(self, project_root: str) -> ProjectContext:
        return ProjectContext()

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return [SourceFile("src/generated/schema.ts", "export interface User { name: string; }")]


def main() -> int:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "src").mkdir()
        (root / "tsconfig.json").write_text(
            json.dumps(
                {
                    "compilerOptions": {"strict": True, "noEmit": True},
                    "include": ["src/**/*.ts"],
                }
            )
        )
        result = check_project(root, adapter=ComponentTool())
        error = result.errors[0]
        assert (error.code, error.file, error.line, error.column) == (
            2322,
            "src/Widget.component",
            5,
            14,
        )
        print(f"Component: {error.file}:{error.line}:{error.column}: TS{error.code}")
        (root / "src/main.ts").write_text(
            "import type { User } from './generated/schema'; "
            "export const user: User = {name: 'Ada'};"
        )
        assert check_project(root, adapter=SchemaTool()).success
        assert not (root / "src/generated/schema.ts").exists()
        assert not list(root.glob(".pytscheck-*"))
        print("Schema: real project imported generated types; original files preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
