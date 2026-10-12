# Frequently asked questions

## Do users need Node.js or Go?

No for installed platform wheels. The compiler is already bundled. A TypeScript project's dependencies may still need its usual package workflow, and building from source can download a compiler archive from npm.

## Is this a transpiler or bundler?

The default workflow type-checks with `--noEmit`. It returns diagnostics, not JavaScript bundles. Transpiling successfully does not establish that TypeScript types are correct.

## Which TypeScript version runs?

The pinned native compiler `7.0.0-dev.20260707.2`. It does not use a globally installed `tsc`. Check `python -m pytscheck --version` and the [compatibility guide](compatibility.md).

## Does checking contact a cloud service?

The checking API invokes a local executable. Wheel installation, source-build compiler downloads, and project dependency installation are separate operations.

## Why is `pip install pytscheck` unavailable or not selecting this release?

The documented version is an initial release. It must be published first, and prerelease selection may require an exact version or `--pre`. Before publication, install the matching downloaded wheel.

## Can I check a string that imports my files?

Strings run in a private temporary directory. Use file/project checks for an existing import graph, or supply generated files through an adapter.

## Does it honor tsconfig?

`check_project` reads the root config and passes it to the compiler, with wrapper flags that can override settings. It does not search parent configs automatically or build project references. See [configuration](configuration.md).

## Can I set a timeout or enable async checking?

There is no public timeout or async API. Each call is synchronous with runtime defaults. A host application can execute checks in its own worker/thread and limit concurrency; each call launches a compiler process.

## Are source maps fully supported?

Source-map v3 VLQ positions, multiple sources, and inline indexed sections are supported. A consuming tool supplies correct maps; unmapped positions stay generated. External section URLs are not fetched. See [project-aware adapters](adapter-projects.md).

## Is untrusted code safe to check?

The wrapper has validation and subprocess limits, but it is not a sandbox. Use operating-system isolation for hostile projects and only discover trusted adapter packages.

## How do I publish?

Follow [publishing](publishing.md). Upload the source archive and all nine wheels for the intended version. Compiler ZIPs are separate downloads, not PyPI distributions.
