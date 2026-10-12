# Compatibility

## Python and systems

The package declares Python 3.11+. CI exercises Python 3.11, 3.12, and 3.13 on Linux, plus native compatibility and wheel installation checks on Windows and macOS. Declared support for a newer interpreter is not evidence of a separate native CI run.

See [supported platforms](supported-platforms.md) for the six wheel targets. x86/32-bit Python, musl Linux such as Alpine, and unlisted OS/CPU combinations do not have dedicated supported wheels.

## Compiler pin

The compiler is `7.0.0-dev.20260707.2`, a pinned native TypeScript preview build. It is not selected from your PATH and is not your npm project's `typescript` package. Installed Node.js or Go versions do not choose the compiler.

TypeScript semantics, flags, diagnostics, and configuration compatibility follow this pin. Do not assume a project accepted by an older `tsc` behaves identically; inspect compiler diagnostics and conformance differences. Standard-library declarations travel with the compiler.

## Supported wrapper workflows

- Source strings, existing files, and root-configured projects.
- Structured diagnostics and CLI JSON.
- Global compiler options and selected additional flags.
- Generated sources through third-party adapters.

## Limits

The wrapper does not build referenced projects, run a language server, transpile for a bundler, watch files, or offer incremental sessions. It supports source-map v3 VLQ positions and inline indexed maps; external indexed section URLs must be resolved by the consuming tool. The CLI exposes fewer knobs than the Python API.

The defaults force strict/no-emit flags. A string tsconfig `extends` path outside the supplied project root is rejected. Legacy isolated adapter checks do not inherit project settings/dependencies. Optional ProjectContext enables project-aware checking and Python declaration resources. These constraints matter when migrating a monorepo or component pipeline.

[Compiler upgrades](compiler-upgrade.md) must be validated with actual binary downloads, conformance diffs, and native CI.
