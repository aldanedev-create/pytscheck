# Architecture

Each public check is synchronous and invokes one bundled native compiler process. PyTSCheck supplies orchestration and diagnostic normalization; the TypeScript type system comes from `tsgo`.

## Checking pipeline

| Layer | Responsibility |
| --- | --- |
| `api.py` | Public entry points, option coercion, path validation, adapter orchestration |
| `checker.py` | Prepare source files/arguments, invoke runner, validate exit/output behavior |
| `runner.py` | Find platform binary, enforce timeout/output limits, capture streams, cleanup |
| `protocol.py` | Parse plain compiler diagnostics and reject unrecognized output |
| `results.py`, `models.py` | Build typed immutable result/diagnostic objects |
| `config.py`, `resolver.py`, `project.py` | Project configuration and fallback source discovery |
| `adapters/` | Source contract, registration/discovery, original filename remapping |

## Input modes

A source string is written into a temporary directory. A disk file is checked where it exists. A project uses its root tsconfig or passes a discovered file list. An adapter supplies virtual sources checked together in a temporary directory. Its optional `ProjectContext` enables inherited project settings, real-file imports, and declaration resources; adapters without context retain isolated checking.

The runner passes an argument list with `shell=False` and appends `--pretty false`. It captures stdout/stderr to temporary files, polls their sizes, and reads bounded output. Compiler exit/output checks prevent a crash or empty failing output from becoming success.

On POSIX, the compiler starts in a new session and its process group is killed during cleanup. On Windows, cleanup kills the main process when needed; there is no Windows Job Object sandbox.

## Distribution

A custom Hatch build hook chooses one platform, verifies the pinned compiler hash, and force-includes that compiler, declarations, and a one-platform manifest. Wheels are tagged `py3-none-<platform>` because they contain a native executable but no Python extension ABI. The source archive excludes bundled platform directories and may fetch the compiler when built.

Importing `pytscheck` does not launch the compiler. There is no persistent compiler service, compiler result cache, watch mode, network checking service, or hosted compiler service. Adapter source maps support v3 VLQ positions and inline indexed sections. See [binary distribution](binary-distribution.md) and [security](security.md).

Context-aware adapters resolve inherited configuration, snapshot project sources into a unique temporary directory under the project root, and add generated sources/declaration resources. Original files are preserved, and normal ancestor dependency lookup remains available. See [project-aware adapters](adapter-projects.md).
