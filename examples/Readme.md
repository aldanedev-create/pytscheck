# Examples

Runnable examples of every public API. Each file is a standalone script that produces real output when run.

## Running

From the repository root, with the package installed:

```bash
pip install -e .

# Fetch the bundled compiler once (Phase 0)
python scripts/build_binaries.py linux-x64   # or win32-x64, darwin-arm64, ...

# Run any example
python examples/check_string.py
```

Each example prints something useful and exits 0 on success. None requires arguments. Several accept optional ones for exploration.

## Index

| File | What it shows |
| --- | --- |
| `check_string.py` | Check an in-memory TypeScript source string |
| `check_file.py` | Check a single `.ts` file on disk |
| `check_project.py` | Check a project directory via `tsconfig.json` |
| `custom_options.py` | Pass `CompilerOptions` to control strictness, target, module |
| `diagnostic_reporting.py` | Format diagnostics for humans and machines |
| `ci_validation.py` | Fail a build on type errors (suitable for CI) |
| `editor_integration.py` | Minimal editor-style diagnostics pipeline |
| `custom_adapter.py` | Write an adapter for a custom TypeScript-generating format |

## What the examples are not

They are **not tests.** Tests live under `tests/` and assert behavior. Examples demonstrate usage and print output a human can read.

They are **not exhaustive.** They cover the common cases — the API has more surface, documented in `docs/python-api.md`.

They are **not tutorials.** Each file is self-contained and short, with comments explaining what and why. Read the source.

## Example: the smallest useful script

```python
from pytscheck import check

result = check('const age: number = "twenty";')
print(result.success)                 # False
for d in result.errors:
    print(d.line, d.column, d.code, d.message)
```

That's it. Everything else in this directory is a variation on this pattern.

## Adapter example

`custom_adapter.py` is different from the others: it shows how a consuming tool integrates with PyTSCheck. If you maintain a Python tool that generates or transforms TypeScript, this is the example to read first.

For the full adapter guide, see `src/pytscheck/integrations/README.md`.