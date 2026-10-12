# Examples

Install the package and compiler using [development setup](../docs/development.md). Run scripts from the repository root. Most create temporary demonstration inputs; `editor_integration.py` accepts a file path and `ci_validation.py` accepts a real project path and exits according to its result.

| Script | Demonstration |
| --- | --- |
| [check_string.py](check_string.py) | Source-string checks |
| [check_file.py](check_file.py) | A TypeScript file on disk |
| [check_project.py](check_project.py) | A configured project |
| [custom_options.py](custom_options.py) | Strictness, target, module and libraries |
| [diagnostic_reporting.py](diagnostic_reporting.py) | Human/machine reports |
| [ci_validation.py](ci_validation.py) | Build failure from a real project check |
| [editor_integration.py](editor_integration.py) | Editor-style reporting, not a language server |
| [custom_adapter.py](custom_adapter.py) | Toy component extraction into virtual TypeScript |

```bash
python examples/check_string.py
python examples/check_file.py
python examples/check_project.py
python examples/custom_options.py
python examples/diagnostic_reporting.py
python examples/editor_integration.py tests/fixtures/projects/minimal/main.ts
python examples/custom_adapter.py
python examples/ci_validation.py tests/fixtures/projects/minimal
```

Examples demonstrate API use and may deliberately print type errors; a demonstration can exit `1` for those expected diagnostics. They do not replace tests. The toy adapter is not a production component parser or a source-map implementation; see [adapters](../docs/adapters.md) for current limits.
