#!/usr/bin/env python3
"""Write an adapter for a custom TypeScript-generating format.

This example defines a tiny "component" format — a file with a
``<script>`` block containing TypeScript — and shows how to plug an
adapter into PyTSCheck so that diagnostics point at the original
component file rather than at the extracted TypeScript.

Run it:

    python examples/custom_adapter.py

The script writes two components into a temp directory, one clean and
one with a type error, then checks the directory through the adapter.

To use a real adapter in your own tool:

    1. Define a class with `name` and `get_sources`.
    2. In your tool's `pyproject.toml`, add an entry point under
       `pytscheck.adapters` that resolves to the class.
    3. Users install your tool with an extra that pulls in pytscheck:
       `pip install yourtool[typecheck]`.

See src/pytscheck/integrations/README.md for the full guide.
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

from pytscheck import check_project
from pytscheck.adapters.errors import AdapterExtractionError
from pytscheck.adapters.sources import collect_sources
from pytscheck.checker import check_sources_virtual
from pytscheck.models import SourceFile


# ---------------------------------------------------------------------------
# A toy component format
# ---------------------------------------------------------------------------


_SCRIPT_RE = re.compile(r"<script[^>]*>(?P<body>.*?)</script>", re.DOTALL)


class ComponentAdapter:
    """Extract the ``<script>`` block from a ``.component`` file.

    Implements the CompilerAdapter protocol. Produces one SourceFile per
    component, with ``origin_path`` pointing at the original file so
    diagnostics are reported there.
    """

    @property
    def name(self) -> str:
        return "component-demo"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        root = Path(project_root)
        if not root.is_dir():
            raise AdapterExtractionError(f"not a directory: {project_root}")

        sources: list[SourceFile] = []
        for path in sorted(root.rglob("*.component")):
            text = path.read_text(encoding="utf-8")
            match = _SCRIPT_RE.search(text)
            if match is None:
                raise AdapterExtractionError(
                    f"no <script> block found in {path.name}"
                )
            body = match.group("body")
            rel = path.relative_to(root).as_posix()
            sources.append(
                SourceFile(
                    path=f"__components__/{rel}.ts",
                    text=body,
                    origin_path=rel,
                    kind="generated",
                )
            )
        return sources


# ---------------------------------------------------------------------------
# Sample project
# ---------------------------------------------------------------------------


CLEAN_COMPONENT = """\
<template>
  <div>Hello</div>
</template>

<script>
export const message: string = "hello";
export function greet(): string { return message; }
</script>
"""

BROKEN_COMPONENT = """\
<template>
  <div>Counter</div>
</template>

<script>
const count: number = "not a number";   // <-- type error
export { count };
</script>
"""


def _write_demo_project(root: Path) -> None:
    (root / "Greeting.component").write_text(CLEAN_COMPONENT, encoding="utf-8")
    (root / "Counter.component").write_text(BROKEN_COMPONENT, encoding="utf-8")
    # The compiler still needs a tsconfig; PyTSCheck writes a virtual
    # project for the adapter case, but a tsconfig here keeps the
    # project's structure realistic.
    (root / "tsconfig.json").write_text(
        '{"compilerOptions": {"strict": true, "noEmit": true}}',
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def main() -> int:
    root = Path(tempfile.mkdtemp(prefix="pytscheck-adapter-demo-"))
    _write_demo_project(root)

    print(f"Demo project: {root}")
    for p in sorted(root.iterdir()):
        print(f"  {p.name}")
    print()

    adapter = ComponentAdapter()

    # 1. Collect sources (this is what the adapter does)
    print("Step 1: collect sources through the adapter")
    sources = collect_sources(adapter, str(root))
    for s in sources:
        print(f"  {s.origin_path}  ->  {s.path}  ({len(s.text)} bytes)")
    print()

    # 2. Check them (as pytscheck does internally when an adapter is used)
    print("Step 2: check the collected sources")
    result = check_sources_virtual(sources)
    print(f"  success: {result.success}")
    print(f"  diagnostics: {len(result.diagnostics)}")
    print()

    # 3. Remap diagnostics to the original files
    from pytscheck.adapters.source_maps import remap_diagnostics

    remapped = remap_diagnostics(result.diagnostics, sources)
    for d in remapped:
        file = d.file or "<global>"
        origin = f"  (origin: {d.origin_file})" if d.origin_file else ""
        print(f"  {file}:{d.line}:{d.column}  TS{d.code}: {d.message}{origin}")
    print()

    # 4. The same result through the public API
    print("Step 3: check_project(..., adapter=...)")
    public = check_project(root, adapter=ComponentAdapter())
    print(f"  success: {public.success}")
    for d in public.errors:
        print(f"  {d.file}:{d.line}:{d.column}  TS{d.code}: {d.message}")
    print()

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())