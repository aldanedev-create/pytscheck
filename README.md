
# PyTSCheck

**Python-native TypeScript type checking.** Powered by a bundled native `tsgo` compiler.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-pre--alpha-orange)](#status)

> **Status: pre-alpha.** Interfaces are being defined; nothing is published to PyPI yet. Follow the repository for progress.

---

## What it is

PyTSCheck makes TypeScript type checking available through a conventional Python API — **without requiring users to install Node.js or Go**.

It bundles Microsoft's native TypeScript compiler (`tsgo`, the Go rewrite shipped with TypeScript 7.0) inside platform-specific wheels and drives it from Python. You hand it a source string, a file, or a project directory; you get back structured diagnostics as typed Python objects.

It also defines a **compiler-agnostic adapter protocol** so that Python tools which *generate* or *transform* TypeScript (template compilers, single-file-component toolchains, schema-to-code generators) can submit their sources to PyTSCheck and receive diagnostics mapped back to the original files.

## Why

Python developers who build tooling around TypeScript currently must:

- manage a JavaScript runtime and a compiler install,
- invoke external commands,
- parse diagnostic output themselves,
- handle platform differences,
- and then *still* not have type checking at all if their tool only transpiles.

Translation alone does not prove a program is type-correct. A `.ts` file can transpile cleanly to JavaScript and still contain a type error the transpiler silently discarded.

PyTSCheck solves this with:

- **one reusable Python interface**,
- **a bundled native compiler** (install with `pip`, no Node, no Go),
- **a common adapter protocol** so any Python tool can reuse the checker.

## Install

```bash
pip install pytscheck
```

No separate Go or Node.js install is required. Each wheel bundles the correct `tsgo` binary and TypeScript standard-library declarations for its platform.

## Quick start

### Check a source string

```python
from pytscheck import check

result = check('const age: number = "twenty";')

print(result.success)   # False
for diagnostic in result.errors:
    print(diagnostic.line, diagnostic.column, diagnostic.code, diagnostic.message)
```

### Check a file

```python
from pytscheck import check_file

result = check_file("src/app.ts")

if not result.success:
    for d in result.errors:
        print(f"{d.file}({d.line},{d.column}): {d.category} TS{d.code}: {d.message}")
```

### Check a project

```python
from pytscheck import check_project

result = check_project("./my-project")

if not result.success:
    for d in result.errors:
        print(d.message)
```

Project checking respects `tsconfig.json`, project references, declaration files, and module resolution.

### Check a project through an adapter

```python
from pytscheck import check_project
from teloc.typecheck import TelocAdapter

result = check_project(".", adapter=TelocAdapter())

for error in result.errors:
    # Points at the original .vel file, not the extracted TypeScript
    print(error.file, error.line, error.column, error.message)
```

Adapters are built by the consuming tool. PyTSCheck defines the protocol and never imports a specific adapter.

## Command-line interface

A small CLI is available for smoke tests, CI scripts, and editor integration:

```bash
pytscheck --version                  # print versions
pytscheck --where                    # print the bundled tsgo path
pytscheck string 'const x: number = "a"'
pytscheck file src/app.ts
pytscheck project ./my-project
pytscheck project ./my-project --json
```

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Success — no errors |
| `1` | Type errors were reported |
| `2` | Usage error (bad arguments, bad config) |
| `3` | Operational error (missing binary, timeout, crash, unparsable output) |

The 1-vs-3 distinction matters for CI: **1 means the TypeScript is bad; 3 means the tooling is broken.**

## Public API

The public surface is small and stable. Everything below is exported from `pytscheck`:

| Name | Purpose |
|---|---|
| `check(source, *, filename="input.ts", options=None, keep_raw=False)` | Check an in-memory TypeScript source string |
| `check_file(path, *, options=None, keep_raw=False)` | Check a single file on disk |
| `check_project(project_root, *, options=None, adapter=None, keep_raw=False)` | Check a project directory (optionally via an adapter) |
| `CompilerOptions` | Compiler-option configuration |
| `Result`, `Diagnostic`, `RelatedInformation`, `SourceFile` | Typed result and source models |
| `PyTSCheckError` and subclasses | Exception hierarchy |
| `__version__`, `COMPILER_VERSION`, `ADAPTER_PROTOCOL_VERSION` | Version metadata |

Adapter authors import from `pytscheck.adapters`; the core package never imports a specific adapter.

### Design rule: no silent successes

The library is built so that:

- **Type errors** are returned as `Diagnostic` objects in `Result.diagnostics` — never raised.
- **Operational failures** (missing binary, crash, timeout, unparsable output) raise `PyTSCheckError` subclasses — never returned as `Result(success=True)`.
- **Adapter extraction failures** raise `AdapterExtractionError` — never reported as type errors.

A transpiler that cannot produce TypeScript raises; it does not invent a `Diagnostic` and mislead the caller's CI.

## Platform support

| OS | Architecture | Status |
|---|---|---|
| Linux | x86-64 | target |
| Linux | ARM64 | target |
| macOS | Intel | target |
| macOS | Apple Silicon | target |
| Windows | x86-64 | target |
| Windows | ARM64 | deferred |

Each wheel bundles only its own platform's binary and `.d.ts` files. No network access is required after installation. Binaries are fetched at build time from the npm registry and verified against the registry's SHA-512 integrity value.

## Writing an adapter

If you maintain a Python tool that generates, extracts, or transforms TypeScript, you can wire it into PyTSCheck in a few lines.

```python
from pytscheck.adapters.base import CompilerAdapter
from pytscheck.models import SourceFile


class MyAdapter:
    @property
    def name(self) -> str:
        return "mytool"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return [
            SourceFile(
                path="generated/App.ts",           # virtual path the checker sees
                text=extracted_typescript,          # the TypeScript to check
                origin_path="src/App.vue",          # real file the user cares about
                kind="generated",
            )
        ]
```

Register it via the `pytscheck.adapters` entry-point group:

```toml
[project.optional-dependencies]
typecheck = ["pytscheck>=0.1.0"]

[project.entry-points."pytscheck.adapters"]
mytool = "mytool.typecheck:MyAdapter"
```

Users then opt in with `pip install mytool[typecheck]`.

Full guide: [`src/pytscheck/integrations/README.md`](src/pytscheck/integrations/README.md).

### The honesty rule

If your tool cannot produce TypeScript for one of its inputs, raise `AdapterExtractionError`. Do not return an empty source list. Do not fabricate a `Diagnostic`. A build summary that counts an extraction failure as "1 type error" is a lie.

## Development

```bash
git clone https://github.com/aldanedev-create/pytscheck
cd pytscheck
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install

# Fetch the bundled compiler for your platform (Phase 0)
python scripts/build_binaries.py linux-x64   # or win32-x64, darwin-arm64, ...
python scripts/verify_binaries.py

# Run the suite
pytest

# Lint, format, and type-check
ruff check src tests scripts
ruff format src tests scripts
mypy src/pytscheck
```

Or via the task runners: `make dev`, `make test`, `make lint`, `make type`, `task test`, or `nox -s tests`.

### Project layout

```
pytscheck/
├── src/pytscheck/         # the Python package
│   ├── api.py             # public entry points
│   ├── checker.py         # orchestration
│   ├── runner.py          # subprocess invocation of the bundled binary
│   ├── protocol.py        # parser for tsgo output
│   ├── models.py          # Diagnostic, Result, SourceFile
│   ├── adapters/          # the compiler-agnostic adapter system
│   └── bin/               # bundled tsgo binaries (fetched at build time)
├── tests/                 # unit, integration, adapter, security, fuzz suites
├── conformance/           # compiler conformance cases
├── benchmarks/            # startup, throughput, memory, concurrency benchmarks
├── scripts/               # binary fetching, verification, release tooling
├── docs/                  # user and developer documentation
└── examples/              # runnable usage examples
```

See [`docs/architecture.md`](docs/architecture.md) for the three-layer design (Python API, native compiler, adapter layer).

## Testing

The test suite has roughly 1,300 tests organized into layers:

- **`tests/`** — unit and integration tests that exercise real subprocesses and real files.
- **`tests/unit/`** — contract and invariant tests for the public API.
- **`tests/adapters/`** — the adapter protocol, registry, discovery, and source-map remapping.
- **`tests/integration/`** — end-to-end tests with the real bundled compiler.
- **`tests/compatibility/`** — platform and compiler-version parity.
- **`tests/security/`** — hostile inputs, symlink escapes, JSON bombs, resource limits, temp-file hygiene.
- **`tests/fuzz/`** — randomized and hostile-input testing of the parser.

No test mocks the compiler. Where a test needs real diagnostics, it runs the real bundled `tsgo`. Where a test cannot run without the binary, it skips with a clear message.

## Design principles

1. **Python-first API, independent of the compiler's command line.** All knowledge of tsgo's CLI and output format lives in a small set of modules, so a future programmatic API can replace them without changing the public surface.
2. **No silent successes.** Operational failures raise. Adapter extraction failures raise. `Result.success` means exactly what it says.
3. **Bundled, not downloaded.** No network access at runtime. The compiler is inside the wheel.
4. **Agnostic adapters.** The core never imports a specific consumer. Adapters live in the consuming package.
5. **Verify the compiler distribution before code.** Pin the version. Verify the checksum. Test the layout. Only then build.
6. **Adapters built last, with one concrete consumer first.** Design the protocol after it has a real user, not before.

## Roadmap

Work proceeds in phases defined in the project specification:

- **Phase 0** — verify the tsgo distribution and its output format.
- **Phase 1** — bundle and run the compiler end to end.
- **Phase 2** — runner, parser, and `check()`.
- **Phase 3** — `check_file()`, `check_project()`, result models, configuration.
- **Phase 4** — distribution: platform wheels and clean-install tests.
- **Phase 5** — adapter system and the first consumer adapter.
- **Phase 6** — stability: conformance, fuzz, security hardening, documentation.

## Success criteria

The project is successful when:

1. Users can install PyTSCheck from PyPI without installing Go or Node.js.
2. It correctly reports type errors for supported TypeScript programs.
3. The public API returns consistent structured diagnostics.
4. Complete supported projects can be checked with the required compiler options.
5. A consuming Python tool can supply sources via the adapter interface and receive diagnostics mapped to its own files.
6. Published wheels work on their declared operating systems and architectures.
7. Compiler upgrades are validated by conformance and regression tests.
8. Failures are reported explicitly rather than mistaken for successful checks.
9. The package remains maintainable without implementing its own TypeScript type system.

## Non-goals

PyTSCheck explicitly does **not**:

- reimplement the TypeScript type system in Python,
- execute TypeScript programs,
- bundle third-party compilers or frameworks,
- recover type information from already-transpiled JavaScript,
- automatically repair type errors,
- ship a custom Go integration layer (deferred until the bundled compiler proves insufficient).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). By participating you agree to the [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Security

See [`SECURITY.md`](SECURITY.md). Report vulnerabilities privately via GitHub Security Advisories.

## Support

See [`SUPPORT.md`](SUPPORT.md).

## Governance

See [`GOVERNANCE.md`](GOVERNANCE.md).

## License

Apache-2.0. See [`LICENSE`](LICENSE).

The bundled `tsgo` binaries are redistributed under their own Apache-2.0 terms; see [`NOTICE.txt`](NOTICE.txt).

## Acknowledgments

The TypeScript native compiler is developed and maintained by Microsoft and the TypeScript team. PyTSCheck redistributes the compiler binaries unmodified and provides a Python interface to them.
