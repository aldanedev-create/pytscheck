# PyTSCheck documentation

PyTSCheck exposes a Python API and CLI over a bundled native TypeScript compiler. Start with installation and the quick start, then choose a guide for your workflow.

## Use the package

| Guide | What you will learn |
| --- | --- |
| [Installation](installation.md) | Wheels, source checkouts, offline installs, Windows setup |
| [Quick start](quickstart.md) | Check strings, files, projects, and handle failures |
| [Python API](python-api.md) | Public functions, models, exceptions, version constants |
| [JavaScript and JSDoc](jsdoc.md) | Check JavaScript types using JSDoc annotations |
| [CLI](cli.md) | Commands, JSON output, exit codes |
| [Configuration](configuration.md) | Defaults, tsconfig discovery, precedence |
| [Compiler options](compiler-options.md) | Every `CompilerOptions` field and extra flags |
| [Project checking](project-checking.md) | Imports, declarations, aliases, project references |
| [Diagnostics](diagnostics.md) | Error codes, positions, raw output, JSON serialization |
| [Adapters](adapters.md) | Generated sources, registration, mapping limitations |
| [Compatibility](compatibility.md) | Python versions, pinned compiler, unsupported features |
| [Supported platforms](supported-platforms.md) | Platform identifiers and wheel tags |
| [Troubleshooting](troubleshooting.md) | Installation, configuration, runtime, and adapter failures |
| [FAQ](faq.md) | Common questions and practical limits |

## Maintain and publish

| Guide | What you will learn |
| --- | --- |
| [Architecture](architecture.md) | How sources become diagnostics |
| [Security](security.md) | Trust boundaries, limits, isolation |
| [Development](development.md) | Local environment and repository layout |
| [Testing](testing.md) | Serial tests, fixture gates, conformance, CI |
| [Performance](performance.md) | Real benchmark runs and interpreting results |
| [Binary distribution](binary-distribution.md) | Compiler downloads, checksums, self-contained wheels |
| [Compiler upgrades](compiler-upgrade.md) | Update pins and review semantic drift |
| [Publishing](publishing.md) | Build/download all artifacts and upload to PyPI |
| [Release validation](release-validation-2026-10-12.md) | Dated evidence for the development release |

The current package is `0.1.0`; the compiler is `7.0.0-dev.20260707.2`. The release workflow builds distributions but does not upload them to PyPI.
