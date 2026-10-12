# Security and runtime limits

PyTSCheck checks code locally using a bundled executable. Checking a project gives the compiler access to files visible to the current operating-system user. Run hostile repositories in a restricted process/container with appropriate filesystem and resource limits.

## Existing protections

- Subprocess arguments use a list and `shell=False`.
- Source-string and single-file checks reject NUL bytes and input above 8 MiB.
- Adapter source paths reject absolute/drive-qualified paths, `..`, NUL bytes, and exact duplicates.
- A string tsconfig `extends` path resolving outside the supplied root is rejected.
- Compiler downloads and on-disk binaries are checked against recorded SHA-512 values.
- Temporary source/output files are cleaned up, and output is read within bounded limits.

| Runtime default | Value | Applies to |
| --- | --- | --- |
| Timeout | 60 seconds | Each runner invocation |
| Stdout limit | 32 MiB | Captured compiler stdout |
| Stderr limit | 4 MiB | Captured compiler stderr |
| Source limit | 8 MiB | `check()` and `check_file()` prevalidation |
| Input count | 20,000 files | Project scan without a tsconfig |

Output limits are detected by polling temporary-file sizes; a fast producer can briefly write beyond a limit before termination. These are wrapper defaults, not public `CompilerOptions` fields or guarantees of total memory/CPU/disk use. Configured projects and adapter sources do not receive the same per-source prevalidation as single-source entry points.

## Trust boundaries

These checks do not sandbox compiler filesystem access, symlinks, dependencies, configuration, or imported adapter code. Adapter discovery executes installed plugin code. Custom compiler flags can alter behavior; keep no-emit enabled for checking workflows.

POSIX cleanup terminates the compiler process group. Windows cleanup targets the main process; it does not promise that arbitrary descendants are terminated. Use operating-system isolation when stronger cleanup/resource guarantees are needed.

No source is sent to a hosted checker by this API. Source-build downloads and dependency installation are separate network operations. Raw diagnostics may contain private paths and source excerpts; avoid publishing them without review.

Report vulnerabilities through the repository's [security policy](../SECURITY.md).
