# Python API reference

Import supported entry points from `pytscheck`. The same checking functions are available from `pytscheck.api`. Internal runner/checker modules are not the stable end-user API.

## Checking functions

```text
check(source, *, filename="input.ts", options=None, keep_raw=False)
check_file(path, *, options=None, keep_raw=False)
check_project(project_root, *, options=None, adapter=None, keep_raw=False)
```

| Argument | Contract |
| --- | --- |
| `source` | TypeScript source string; NUL bytes and oversized input are rejected |
| `filename` | Non-empty bare filename; defaults to `input.ts`; paths are rejected |
| `path` | `str` or `pathlib.Path` identifying an existing file |
| `project_root` | `str` or `pathlib.Path` identifying an existing directory |
| `options` | `CompilerOptions`, a dictionary of its fields, or `None` |
| `adapter` | Optional `CompilerAdapter` instance; only for project checking |
| `keep_raw` | Attach compiler text to `Result.raw_output`; default `False` |

All three functions return `Result`. Unknown function keyword arguments are rejected by Python. The compiler runs synchronously in a subprocess for each check. There is no public `timeout=` parameter, async function, cache, or incremental session.

## CompilerOptions

Malformed option containers and values raise `ConfigurationError`. A frozen dataclass with `strict`, `no_emit`, `skip_lib_check`, `types`, `lib`, `target`, `module`, `module_resolution`, and `extra`. See the full [field table](compiler-options.md). Dataclass freezing is shallow; avoid mutating a shared `extra` dictionary.

## Result

A frozen, slotted dataclass:

| Field/property | Type | Meaning |
| --- | --- | --- |
| `success` | `bool` | Completed check with no error diagnostics |
| `diagnostics` | `tuple[Diagnostic, ...]` | All normalized diagnostics |
| `compiler_version` | `str` | Pinned compiler identifier |
| `elapsed_seconds` | `float` | Compiler invocation duration |
| `raw_output` | `str` or `None` | Compiler text when requested |
| `errors` | `tuple[Diagnostic, ...]` | Diagnostics whose category is `error` |
| `warnings` | `tuple[Diagnostic, ...]` | Diagnostics whose category is `warning` |

Operational failures raise; they are never a successful `Result`. A successful result does not guarantee runtime correctness.

## Diagnostic and RelatedInformation

`Diagnostic` fields are `file`, `line`, `column`, `code`, `category`, `message`, `end_line`, `end_column`, `related`, and `origin_file`. `is_error` and `is_warning` are convenience properties. `category` is `error`, `warning`, `suggestion`, or `message`.

`RelatedInformation` holds `file`, `line`, `column`, and `message`. Locations are 1-based for compiler file diagnostics. Global diagnostics have `file=None`; do not interpret their location as a source position. Optional end positions and related information may be absent because the wrapper parses textual diagnostics.

See [diagnostics](diagnostics.md) for reporting and serialization examples.

## SourceFile

`SourceFile(path, text, origin_path=None, source_map=None, kind="source", options={})` describes an adapter's virtual TypeScript input. The default options dictionary is created separately for each instance. `kind` is `source` or `generated`. Per-file `options` are metadata and are not applied as compiler flags. Read [adapters](adapters.md) for validation and mapping behavior.

## Optional adapter project context

```python
from pytscheck.adapters import ProjectContext, DeclarationResource
```

An adapter may implement `get_context(root) -> ProjectContext` alongside `get_sources(root)`. This enables project settings, generated-to-real imports, and declaration files bundled in installed Python packages. Existing adapters require no changes. See [project-aware adapters](adapter-projects.md) for all fields, precedence, source-map v3 mapping, and examples.

## Exceptions

All public exception classes derive from `PyTSCheckError`.

| Exception | Meaning |
| --- | --- |
| `ConfigurationError` | Invalid options, paths, source, or project configuration |
| `UnsupportedPlatformError` | No supported OS/architecture mapping |
| `CompilerNotFoundError` | Bundled executable missing or not executable |
| `CompilerTimeoutError` | Compiler exceeded its time limit |
| `CompilerExecutionError` | Launch failure, crash, output limit, or abnormal execution |
| `OutputParseError` | Compiler output could not be normalized |
| `AdapterError` | Base for adapter failures |
| `AdapterDiscoveryError` | Entry-point discovery/loading failed |
| `AdapterExtractionError` | Adapter could not produce sources |
| `AdapterMappingError` | Invalid mapping input |
| `AdapterProtocolError` | Invalid source contract or incompatible protocol |
| `AdapterRegistrationError` | Missing, duplicate, or invalid registered name |

`CompilerExecutionError` exposes `returncode`, `stdout`, and `stderr`; some failures have no return code. `CompilerTimeoutError` exposes captured `stdout` and `stderr`. Do not expose raw output containing private source text in public logs.

## Version constants

```python
from pytscheck import __version__, COMPILER_VERSION, ADAPTER_PROTOCOL_VERSION
```

They currently identify `0.1.0`, `7.0.0-dev.20260707.2`, and `1.0` respectively. Package, compiler, and adapter protocol versions are separate contracts.
