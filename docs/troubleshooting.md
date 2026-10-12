# Troubleshooting

## Start with versions and binary location

```bash
python --version
python -m pytscheck --version
python -m pytscheck --where
```

Record OS, interpreter architecture, package/compiler versions, the command, and the smallest failing input. Do not include tokens or private source in issue reports.

## Installation issues

| Symptom | What to check |
| --- | --- |
| No matching distribution | Release may not be published; check exact version, Python 3.11+, platform, architecture, and updated pip |
| Wheel is unsupported | Use the wheel matching your Python architecture/OS; do not rename it |
| Compiler missing | Editable/source checkout needs `scripts/build_binaries.py <platform>`; installed wheels may need reinstalling |
| Permission denied | Reinstall an intact wheel; source downloads need executable permissions on POSIX |
| Source build cannot download | Network is needed to fetch the pinned npm archive; use a prebuilt wheel for offline installation |
| Alpine/musl installation fails | No supported musllinux wheel; use a supported glibc environment |

For a source checkout, run `python scripts/verify_binaries.py`. Reinstall only from an artifact whose checksum/contents you trust.

## Configuration and source issues

`ConfigurationError` covers missing paths, NUL bytes, oversized single-source inputs, invalid filenames, empty fallback projects, and malformed project config. `check()` accepts only a basename for `filename`; use `check_file` or `check_project` for imports on disk.

If an `extends` path is rejected, the current wrapper requires string extension targets to resolve inside the supplied project root. Shared configs outside it need a different supported layout; moving the config flag through `extra` is not a supported workaround.

If a project unexpectedly checks in strict mode, the default command-line `--strict` overrides tsconfig. `strict=False` omits the wrapper flag; it does not force tsconfig strictness off. See [configuration](configuration.md).

## Compiler diagnostics

Missing imports often mean project declarations/packages are absent or module resolution is misconfigured. The compiler bundles standard-library declarations, not every external package. `types` selects installed declarations and does not install them.

An invalid compiler option returns a compiler diagnostic if parseable. The pinned native compiler may have removed an option present in older TypeScript versions. An adapter's virtual project cannot automatically see the original root's dependencies or tsconfig.

## Operational failures

`CompilerTimeoutError`, `CompilerExecutionError`, and `OutputParseError` mean the check could not be completed reliably. Check input size, unusual custom flags, disk permissions/space, and the pinned binary. Keep raw output on a completed result with `keep_raw=True`; execution exceptions can expose captured streams.

The runner forces `--pretty false`, including with `FORCE_COLOR=1`. If output parsing still fails, report the exact compiler version and minimal input. Do not catch the error and label the check successful.

## Adapter failures

Use unique relative virtual paths and preserve type information. Empty source lists, duplicates, unsafe paths, wrong entry-point objects, and mismatched protocol majors fail explicitly. Original line/column mapping is not implemented; inspect generated positions rather than assuming a valid source map translates them.

For further help, see [SUPPORT.md](../SUPPORT.md).
