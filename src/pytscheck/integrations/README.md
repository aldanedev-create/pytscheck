# Integrations

Integrations connect Python tools that generate, extract, or transform
TypeScript to PyTSCheck.

Each integration lives in the consuming tool’s package and registers through
the `pytscheck.adapters` entry-point group. This directory documents those
integrations; it contains no integration implementation.

## What an integration does

An adapter provides:

- The TypeScript sources to check.
- The original filenames associated with generated sources.
- Optional source maps for translating diagnostic positions.

PyTSCheck runs the compiler and returns diagnostics. The consuming tool decides
how to display them or whether to fail a build.

Typical consumers include:

- Template engines that extract component script blocks.
- Single-file component compilers.
- Schema-to-TypeScript generators.
- API client generators.
- Python build tools that process TypeScript.

Transpilation and type checking are separate operations. Successfully producing
JavaScript does not establish that the TypeScript passed type checking.

## Installing an integration

A consuming package can provide an optional type-checking extra:

```bash
python -m pip install "yourtool[typecheck]"
```

Declare the dependency and adapter entry point in the consuming package’s
`pyproject.toml`:

```toml
[project.optional-dependencies]
typecheck = ["pytscheck>=0.1.0"]

[project.entry-points."pytscheck.adapters"]
yourtool = "yourtool.typecheck:YourAdapter"
```

Choose a dependency range compatible with the adapter protocol your integration
implements.

Keep PyTSCheck imports inside the optional integration module so that users who
install the tool without the extra can still use its other features.

## Writing an adapter

### 1. Implement the adapter protocol

The adapter protocol is defined by
`pytscheck.adapters.base.CompilerAdapter`.

Because it is a `typing.Protocol`, an adapter can implement it structurally
without inheriting from it.

An adapter provides a name and a method that returns its sources:

```python
from pytscheck.models import SourceFile


class YourAdapter:
    @property
    def name(self) -> str:
        return "yourtool"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        raise NotImplementedError("Implement source discovery and extraction.")
```

Use your tool’s name to reduce registration conflicts.

### 2. Return TypeScript sources

Return a `SourceFile` for each source unit:

```python
from pytscheck.models import SourceFile


def make_source(extracted_typescript: str) -> SourceFile:
    return SourceFile(
        path="components/Button.vel.ts",
        text=extracted_typescript,
        origin_path="components/Button.vel",
        source_map=None,
        kind="generated",
        options={},
    )
```

| Field | Purpose |
| --- | --- |
| `path` | Filename used for the TypeScript source. It must be unique within the returned source list. |
| `text` | TypeScript source with its type information preserved. |
| `origin_path` | Original filename associated with the generated source. |
| `source_map` | Optional mapping from generated positions to original positions. |
| `kind` | Identifies an original or generated source. |
| `options` | Per-file options supported by the implementation. Leave empty unless documented. |

Preserve directory relationships when generated sources import one another.
The checker must also be able to resolve required declarations and dependencies.

### 3. Register the adapter

For published integrations, use the entry point shown above.

For tests and scripts, register an instance explicitly:

```python
from pytscheck.adapters.registry import get_adapter, register_adapter

register_adapter(YourAdapter())

adapter = get_adapter("yourtool")
```

Entry-point discovery and adapter selection are separate concerns. Consult the
registry API for how discovered adapters are loaded.

### 4. Run a check

Pass an adapter instance to PyTSCheck:

```python
from pytscheck import check_project
from yourtool.typecheck import YourAdapter

result = check_project(".", adapter=YourAdapter())

if not result.success:
    for error in result.errors:
        print(error.file, error.line, error.column, error.message)
```

When a diagnostic has a valid source mapping, its position can be translated
back to the original source.

Without a source map, generated positions may not match the original file,
even when the reported filename is `origin_path`.

## Source maps

Extracting or transforming source code can change its positions.

For example, line 12 in generated TypeScript might correspond to line 34 in a
component file. Added imports, removed markup, indentation changes, and reordered
declarations can all affect diagnostic locations.

### Without a source map

Use `source_map=None` when generated positions already match the original source
or when generated positions are acceptable.

Setting `origin_path` associates a filename with the source. It does not, by
itself, describe a line or column offset.

For simple extraction, preserving the original line layout with blank lines can
help retain line numbers. Column positions still require care.

### With a source map

Provide a source map in the format supported by
`pytscheck.adapters.source_maps`.

The map should describe how positions in the generated TypeScript correspond to
positions in the original file.

Validate mappings against representative diagnostics, including:

- Script blocks that start partway through a file.
- Generated imports or declarations.
- Changes in indentation.
- Non-ASCII text.
- Positions with no original-source equivalent.

Follow the implementation’s coordinate conventions. Byte offsets, Unicode
character offsets, and UTF-16 offsets are not interchangeable.

Malformed or unsupported mappings should produce a clear mapping error.
A syntactically valid map can still contain incorrect positions, so adapter tests
must verify mapping accuracy.

## Extraction failures and type errors

Keep extraction failures separate from compiler diagnostics.

An extraction failure means the adapter could not produce the TypeScript it was
expected to check. Examples include:

- An unterminated component script block.
- A schema that cannot be parsed.
- Unsupported input syntax.
- A source file that cannot be read.

Raise `AdapterExtractionError` for these failures:

```python
from pathlib import Path

from pytscheck.adapters.errors import AdapterExtractionError


def read_component(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise AdapterExtractionError(
            f"Could not read component: {path}"
        ) from exc
```

Do not disguise extraction failures as TypeScript diagnostics or silently skip
failed inputs.

An empty source list can be legitimate when a project has no applicable sources.
It must not be used to hide extraction failures.

Type errors belong to the compiler. Examples include:

- Assigning a string to a number variable.
- Calling a function with incompatible arguments.
- Referencing an undefined identifier.
- Omitting a required object property.

Return the TypeScript and let the compiler report these errors.

## Practices to avoid

### Checking only transpiled output

Pass TypeScript before type annotations, interfaces, and type aliases are removed.

JavaScript can support its own type-checking workflows, but checking transpiled
output does not preserve the original TypeScript checking contract.

### Treating transpilation as type-checking success

A transpiler accepting a file does not mean the file passed type checking.

A successful check applies to the sources and compiler options actually checked.
It is not a guarantee of runtime correctness.

### Swallowing extraction failures

Report failed extraction explicitly. Do not return a partial or empty source list
while presenting the operation as a complete check.

### Inventing source positions

Use verified mappings. If a position cannot be mapped, follow the checker’s
documented fallback behavior instead of claiming an exact original position.

### Using generic adapter names

Use a package-specific name such as `yourtool`, rather than `component`.

## Reference implementations

Before naming an integration as a reference implementation, verify that its
package, adapter import path, registration name, and tests exist.

A useful reference adapter should demonstrate:

- Source discovery.
- TypeScript extraction.
- Dependency resolution.
- Original filename reporting.
- Source-map generation and validation.
- Extraction error handling.
- Entry-point registration.

## Protocol compatibility

If your PyTSCheck version supports adapter protocol version declarations,
declare the version your adapter implements and test compatibility handling.

Use the repository’s documented versioning policy and changelog to determine
which releases your integration supports.

## Testing an integration

Include tests for:

- Valid inputs.
- Type errors in extracted TypeScript.
- Extraction failures.
- Projects with no applicable sources.
- Imports between generated sources.
- Original filename and position mapping.
- Entry-point discovery in an installed package.
- Operation without the optional type-checking dependency.

## Further reading

- [Adapter development guide](../../../docs/adapters.md)
- [Architecture](../../../docs/architecture.md)
- [Custom adapter example](../../../examples/custom_adapter.py)
- [Governance](../../../GOVERNANCE.md)

## Packaging this documentation

If this README should be included in published distributions, configure the
active build backend to include it.

For a setuptools source distribution using `MANIFEST.in`, add:

```text
recursive-include src/pytscheck/integrations *.md
```

Wheel inclusion is controlled separately by the build backend. Inspect both the
built source distribution and wheel to confirm this README is present.