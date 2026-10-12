# Project-aware adapters

A consuming tool generates TypeScript or JSDoc JavaScript and provides mapping information. PyTSCheck supplies project configuration, imports, declarations, isolated compiler execution, and diagnostic translation. No framework-specific extraction code belongs in core.

## Opt in without changing existing adapters

The existing `name` and `get_sources(root)` protocol continues to work in isolated mode. Add optional `get_context(root)` to enable project integration:

```python
from pytscheck import SourceFile, check_project
from pytscheck.adapters import ProjectContext

class MyToolAdapter:
    name = "my-tool"
    protocol_version = "1.0"

    def get_context(self, project_root: str) -> ProjectContext:
        return ProjectContext()

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return [SourceFile(
            path="src/generated.ts",
            text="export interface User { name: string; }",
        )]

result = check_project(".", adapter=MyToolAdapter())
```

Virtual paths are relative to the supplied project root. A real `src/main.ts` can import `./generated`, and generated files can import real project files. An existing file with the same virtual path causes `AdapterProtocolError`; PyTSCheck never replaces that file.

## ProjectContext fields

| Field | Default | Purpose |
| --- | --- | --- |
| `tsconfig` | `None` | Root `tsconfig.json`, or an explicit path relative to the project root |
| `inherit_tsconfig` | `True` | Inherit the selected configuration |
| `include_project_files` | `True` | Check its selected real inputs alongside generated sources |
| `compiler_options` | `{}` | Additional settings using TypeScript JSON names, such as `jsx` |
| `declaration_paths` | `()` | Declaration files/directories on disk |
| `declaration_resources` | `()` | Declarations supplied by Python packages |
| `max_workspace_files` | `100000` | Maximum copied/generated workspace files |
| `max_workspace_bytes` | `536870912` | Maximum workspace bytes (512 MiB) |

Setting `include_project_files=False` checks generated entry points and declarations while still making copied real files available for imports.

## Configuration precedence

For context-aware checking, explicit caller options override `ProjectContext.compiler_options`, which override tsconfig, which override defaults. Omitted caller options preserve project strictness and JSX/alias settings. A partial dictionary overrides only its supplied fields:

```python
result = check_project(".", adapter=MyToolAdapter(), options={"target": "es2022"})
```

A `CompilerOptions` instance supplies its boolean defaults as explicit settings. Use a partial dictionary when you want other settings inherited unchanged.

`compiler_options` uses TypeScript names such as `moduleResolution`; the public `options` argument uses Python field names such as `module_resolution`, plus `extra`.

Checks always use plain diagnostics and no emission. An inherited build config with `noEmit:false` is safe to check: checking forces it to true. Explicitly requesting emission through the caller/context raises `ConfigurationError`.

## Configuration inheritance and imports

JSONC comments/trailing commas, parent configuration files, multiple `extends` entries, and npm-package tsconfigs are supported in context mode. Inherited relative alias paths remain relative to the config that defined them, then are rebased into the snapshot when inside the project root. The pinned compiler has removed `baseUrl`; use relative `paths` targets instead, as described in [project checking](project-checking.md).

The native compiler selects original project inputs through `--showConfig`; generated sources and explicit declarations are added. This also supports projects whose original include pattern has no TypeScript inputs until the adapter generates them.

Ordinary packages in the project root's or ancestor `node_modules` remain discoverable. Python-package declarations are a separate supported path and do not require `node_modules` or a Node runtime. Dependencies installed only in a nested subproject may require choosing that subproject as the root or supplying explicit declaration/alias paths.

Choose a root containing the real files used by generated relative imports. This is project checking, not a referenced-project build orchestrator. Prepare any referenced declaration outputs through your build system first.

## PyPI declaration resources

```python
from pytscheck.adapters import DeclarationResource, ProjectContext

context = ProjectContext(
    declaration_resources=(
        DeclarationResource(
            package="my_tool",
            resource="types",
            module="my-tool-runtime",
        ),
    ),
)
```

Here `my_tool` is the installed Python import package. Its resource folder contains `.d.ts`, `.d.mts`, or `.d.cts` files. `module` gives generated code a bare import name:

```typescript
import type { RuntimeContext } from "my-tool-runtime";
```

For directory resources, the module entry comes from `package.json`'s `types` field or `index.d.ts`. For another entry layout, point `resource` directly at the desired declaration file. Resource directories are copied using `importlib.resources`, including zip-installed packages on Python 3.11+.

With `module=None`, declarations are included without installing a module alias. This is useful for globals or files containing `declare module "some-name"`.

To ship declarations in a Hatch-based Python package, place them beneath that package and include the package in its wheel configuration:

```text
my_tool/
    __init__.py
    types/
        index.d.ts
```

Inspect the built wheel to verify the resource files are present. PyPI does not automatically supply types for unrelated JavaScript packages; your tool supplies the appropriate declarations and their licenses.

For declarations on disk:

```python
context = ProjectContext(declaration_paths=("types", "vendor/runtime.d.ts"))
```

## Workspace and cleanup

PyTSCheck creates a unique `.pytscheck-*` directory inside the project root, which must be writable. It copies TypeScript/JavaScript source graphs and package manifests, and JSON data when `resolveJsonModule` is enabled. It avoids `.git`, `node_modules`, build outputs, and common virtual environments. It reads installed dependencies through normal ancestor resolution instead of copying them or creating privileged symlinks.

Original source files are not modified. Each check has a separate workspace; concurrent checks cannot overwrite one another. Workspace cleanup runs after compiler success, diagnostics, validation errors, and timeouts.

This snapshot is not an operating-system sandbox. Configuration and dependencies remain trusted project inputs. Directory symlinks are not traversed. Source symlinks escaping the root and declaration-resource symlinks are rejected. Large projects can set explicit workspace limits. Use a suitable source root and prepared dependency/declaration layout.

## Source maps

Provide standard source-map v3 JSON in `SourceFile.source_map`. PyTSCheck supports Base64 VLQ mappings, multiple original sources, `sourceRoot`, and inline indexed sections. It translates primary/end positions and related diagnostic locations using same-line greatest-lower-bound mappings. Compiler and map columns use UTF-16 coordinates; API locations are 1-based.

For a flat map with one source, `origin_path` can explicitly override its original filename. Multi-source/indexed maps use their mapped source filenames. Unmapped positions retain generated locations; PyTSCheck does not invent a position. Empty legacy maps with no sources preserve the old filename-only behavior.

Maps must be valid JSON/v3 with ordered valid segments and a string `mappings` field, or valid inline sections. Limits are 8 MiB per source/map, 500,000 segments per decoded map, and 16 indexed nesting levels. External section URLs are rejected; resolve them into inline maps in the consuming tool before checking.

A tool must generate correct maps while producing code. A syntactically valid map is not proof that its coordinates match the original content. Include representative diagnostic-position tests in the consuming package.

## Verified consumers

```bash
python examples/adapter_project.py
python examples/check_jsdoc.py
```

The first demonstrates a component tool with a mapped error and a schema tool whose generated declarations are imported by a real project file. Tests additionally cover inherited JSX/JSDoc settings, aliases, generated/real imports, filesystem and zipped Python declaration resources, Unicode positions, concurrency, and cleanup after a real compiler timeout.
