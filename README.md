# PyTSCheck

<p align="center">
  <img src="https://raw.githubusercontent.com/aldanedev-create/pytscheck/03ac50ff57c8e58d7d7f05162f185c6556a25bcb/assets/pytscheck-logo.png" alt="PyTSCheck logo: white PyTS lettering and checkmark on blue" width="180" height="180">
</p>

**Type-check TypeScript from Python, without installing Node.js or Go.**

PyTSCheck wraps Microsoft's native TypeScript compiler, `tsgo`, and returns structured diagnostics for source strings, files, and projects. Platform wheels include the compiler and TypeScript standard-library declarations. The Python runtime has no third-party dependencies.

[Documentation](https://github.com/aldanedev-create/pytscheck/blob/main/docs/index.md) · [Quick start](https://github.com/aldanedev-create/pytscheck/blob/main/docs/quickstart.md) · [Python API](https://github.com/aldanedev-create/pytscheck/blob/main/docs/python-api.md) · [Publishing](https://github.com/aldanedev-create/pytscheck/blob/main/docs/publishing.md)

## Install

Requires Python **3.11 or later** on a [supported platform](https://github.com/aldanedev-create/pytscheck/blob/main/docs/supported-platforms.md).

The current package version is **`0.1.0`**, an initial release. Once that version is published to PyPI:

```bash
python -m pip install --only-binary=:all: "pytscheck==0.1.0"
```

Before publication, install the wheel for your operating system and Python architecture from a successful **Build PyPI distributions** [Actions run](https://github.com/aldanedev-create/pytscheck/actions/workflows/distributions.yml):

```bash
python -m pip install /path/to/pytscheck-platform-wheel.whl
python -m pytscheck --version
```

Replace the example path with the actual downloaded `.whl` filename. See [installation](https://github.com/aldanedev-create/pytscheck/blob/main/docs/installation.md) for Windows, offline installation, and source checkouts.

## Check TypeScript

```python
from pytscheck import check

result = check('export const age: number = "twenty";')
assert not result.success
assert result.errors[0].code == 2322

for error in result.errors:
    print(error.file, error.line, error.column, error.message)
```

Type errors return a `Result`. Missing compilers, invalid configuration, timeouts, and other operational failures raise exceptions.

```python
from pytscheck import CompilerOptions, check_file, check_project

file_result = check_file("src/app.ts")
project_result = check_project(
    ".",
    options=CompilerOptions(target="es2022", module="nodenext"),
)
```

Project checking uses the root `tsconfig.json` when present. Without one, it checks discovered `.ts`, `.tsx`, `.mts`, and `.cts` files, excluding `node_modules`. The defaults enable strict checking and disable emission. See [configuration](https://github.com/aldanedev-create/pytscheck/blob/main/docs/configuration.md) for option precedence and project limitations.

## JavaScript and JSDoc

Check JSDoc-typed JavaScript using a project tsconfig with `allowJs`, `checkJs`, and `noEmit` enabled, then run `pytscheck project .`. Strings and individual `.js` files can also be checked through `CompilerOptions(extra={"allowJs": True, "checkJs": True})`.

See the [JSDoc guide](https://github.com/aldanedev-create/pytscheck/blob/main/docs/jsdoc.md) and `examples/check_jsdoc.py` for working examples.

## Command line

```bash
python -m pytscheck string 'export const x: number = 1;'
python -m pytscheck file src/app.ts --json
python -m pytscheck project .
python -m pytscheck --where
```

The installed `pytscheck` command accepts the same arguments. Exit codes are `0` for success, `1` for compiler errors, `2` for usage/configuration errors, and `3` for operational failures. See the [CLI guide](https://github.com/aldanedev-create/pytscheck/blob/main/docs/cli.md).

## Integrate generated TypeScript

An adapter can provide generated TypeScript through `SourceFile` objects:

```python
from pytscheck import SourceFile, check_project

class GeneratedAdapter:
    name = "example-generated"
    protocol_version = "1.0"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return [SourceFile(path="generated.ts", text="export const x: number = 1;")]

result = check_project(".", adapter=GeneratedAdapter())
assert result.success
```

Adapters live in consuming packages; core does not ship framework integrations. Original filenames can be remapped, but **full source-map position translation is not implemented**. Read the [adapter guide](https://github.com/aldanedev-create/pytscheck/blob/main/docs/adapters.md) before integrating a component compiler.

## Scope and compatibility

- Python 3.11, 3.12, and 3.13 are exercised in CI.
- Six wheels cover Linux, Windows, and macOS on x64 and ARM64. Linux wheels target glibc 2.17+; macOS wheels require macOS 12+.
- The bundled compiler is pinned to **`7.0.0-dev.20260707.2`**. Its TypeScript behavior may differ from another `tsc` or `tsgo` version.
- Checks run locally. Installing a wheel requires no compiler download at check time; building from source can download the pinned binary.
- This is a checker API, not a JavaScript bundler, language server, or incremental build service. Project references are not automatically built with `tsgo -b`.

See [compatibility](https://github.com/aldanedev-create/pytscheck/blob/main/docs/compatibility.md), [security](https://github.com/aldanedev-create/pytscheck/blob/main/docs/security.md), and [troubleshooting](https://github.com/aldanedev-create/pytscheck/blob/main/docs/troubleshooting.md).

## Development and verification

```bash
git clone https://github.com/aldanedev-create/pytscheck.git
cd pytscheck
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install -e ".[dev]"
python scripts/build_binaries.py linux-x64
python -m pytest tests
python conformance/run.py
```

Use your platform identifier instead of `linux-x64`. Run the suite serially; failure tests temporarily replace the compiler. Full setup and release checks are in [development](https://github.com/aldanedev-create/pytscheck/blob/main/docs/development.md) and [testing](https://github.com/aldanedev-create/pytscheck/blob/main/docs/testing.md).

## License and contributions

PyTSCheck is licensed under [Apache-2.0](https://github.com/aldanedev-create/pytscheck/blob/main/LICENSE). Bundled upstream components retain their own licenses and notices. Read [CONTRIBUTING.md](https://github.com/aldanedev-create/pytscheck/blob/main/CONTRIBUTING.md) to contribute and [SECURITY.md](https://github.com/aldanedev-create/pytscheck/blob/main/SECURITY.md) to report vulnerabilities.
