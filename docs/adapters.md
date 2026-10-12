# Adapter development

Adapters let a Python tool provide generated TypeScript to PyTSCheck. They belong to the consuming package, not the core package. Core ships no Teloce, Svelte, Vue, Flask, or Django adapter.

## Implement the contract

```python
from pytscheck import SourceFile, check_project

class ExampleAdapter:
    name = "example-generated"
    protocol_version = "1.0"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return [
            SourceFile(
                path="generated/main.ts",
                text="export const answer: number = 42;",
                kind="generated",
            )
        ]

result = check_project(".", adapter=ExampleAdapter())
assert result.success
```

`name` must be a non-empty string, and `get_sources` must be callable. The protocol is structural, so subclassing is optional. An optional `protocol_version` string must have the same major version as `ADAPTER_PROTOCOL_VERSION`; omission is accepted for the current 1.x protocol.

## SourceFile rules

| Field | Use |
| --- | --- |
| `path` | Unique, non-empty relative virtual filename |
| `text` | TypeScript with type information preserved |
| `origin_path` | Optional original filename |
| `source_map` | Optional JSON mapping metadata; see limitation below |
| `kind` | `source` or `generated` metadata |
| `options` | Metadata; currently not serialized as per-file compiler flags |

Absolute paths, drive-qualified paths, `..` traversal, NUL-containing paths, and exact duplicate paths are rejected. Preserve relative directory relationships for generated imports. Return required generated declarations as additional sources.

The sources are written into a private temporary directory and checked together. The original root's tsconfig and `node_modules` are not copied into that directory. Supply global `CompilerOptions` and the declarations required by the virtual project. Empty sources raise `ConfigurationError`; callers can skip invoking the checker when there is nothing to check.

## Mapping limitations

For a diagnostic whose filename matches `SourceFile.path`, `origin_path` replaces the reported filename and `origin_file` stores the virtual filename. Line and column remain generated coordinates.

When applicable mapping metadata is present, it is validated as a JSON object containing `mappings`. **VLQ decoding and original line/column lookup are not implemented.** A valid source-map string does not enable position translation. Do not advertise accurate component positions unless your adapter preserves line/column layout and verifies the reported paths and positions in real tests.

## Explicit registration

```python
from pytscheck.adapters import get_adapter, register_adapter, unregister_adapter

adapter = ExampleAdapter()
register_adapter(adapter)
assert get_adapter("example-generated") is adapter
unregister_adapter("example-generated")
```

Registration does not make `check_project` auto-select an adapter; pass the selected instance explicitly. Duplicate names raise `AdapterRegistrationError`.

## Package discovery

An integration can expose a class or instance through an entry point:

```toml
[project.entry-points."pytscheck.adapters"]
example-generated = "example_tool.typecheck:ExampleAdapter"
```

Discover explicitly, then choose an instance:

```python
from pytscheck.adapters.discovery import discover_adapters
from pytscheck.adapters import get_adapter
from pytscheck import check_project

discovered = discover_adapters()
result = check_project(".", adapter=get_adapter("example-generated"))
```

The discovery module is not re-exported as `discover_adapters` from the adapters package. Discovery imports installed plugin code; only load trusted packages. Repeated discovery can collide with already registered names.

## Failures and tests

Raise `AdapterExtractionError` when reading/extraction fails rather than silently returning partial inputs. Invalid source contracts, discovery failures, and mapping failures have separate [exception types](python-api.md).

Test a valid input, a type error, extraction failure, unsafe/duplicate paths, empty projects, imports between generated files, real diagnostic filenames, and entry-point discovery in an installed package. Source text and adapter output remain trusted inputs; the checker is not a plugin sandbox.
