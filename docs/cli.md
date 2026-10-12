# Command-line interface

Use `python -m pytscheck` or the installed `pytscheck` console script.

```bash
python -m pytscheck --help
python -m pytscheck --version
python -m pytscheck --where
python -m pytscheck string 'export const x: number = 1;'
python -m pytscheck string 'export const x: number = "bad";' --filename demo.ts --json
python -m pytscheck file src/app.ts --json
python -m pytscheck project . --json
```

Shell quoting differs on Windows. The `file` and `project` subcommands avoid quoting TypeScript text. `--version` reports package, compiler, and adapter protocol versions; `--where` prints the bundled executable path.

## Options

| Command | Arguments/options |
| --- | --- |
| `string` | Required source string; `--filename`, `--json`, `--keep-raw` |
| `file` | Required file path; `--json`, `--keep-raw` |
| `project` | Required root directory; `--json`, `--keep-raw` |

The CLI does not accept compiler flags such as `--strict`, custom adapters, or `--timeout`. Use Python's `CompilerOptions` or a project tsconfig. There is no `check` subcommand; use `string`, `file`, or `project`.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | No compiler errors |
| `1` | Compiler reported errors |
| `2` | Usage or configuration error |
| `3` | Missing/unsupported compiler, crash, timeout, or parse failure |

A CI command can fail a build on any nonzero exit code while reporting infrastructure errors separately from type errors.

## JSON output

`--json` prints an object with `success`, `compiler_version`, `elapsed_seconds`, and a `diagnostics` array. Each diagnostic includes `file`, `origin_file`, `line`, `column`, `end_line`, `end_column`, `code`, `category`, and `message`.

`--keep-raw` requests raw text on the underlying result, but the CLI formatter currently does not include `raw_output` or `related` in its JSON. Use the [Python API](diagnostics.md) to export them. Operational failures print an error to stderr and do not produce a success-shaped JSON object.
