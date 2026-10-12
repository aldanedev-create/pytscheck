# Binary distribution

## What a wheel contains

Each supported platform wheel includes the Python package, exactly one native `tsgo` executable, its TypeScript `.d.ts` libraries, upstream license/notices, and a one-platform manifest. Windows uses `tsgo.exe`. The compiler is selected from the installed package path, not PATH.

Wheels use platform tags with `py3-none`; there is no Python extension ABI or universal `any` wheel. See [supported platforms](supported-platforms.md).

## Fetch and verify

```bash
python scripts/build_binaries.py linux-x64
python scripts/verify_binaries.py
```

The fetch script downloads the pinned npm archive over HTTPS, verifies the upstream archive SHA-512, and records binary SHA-512/size plus archive provenance. Verification checks the actual binary, declarations, and notices. Archive integrity and binary integrity refer to different bytes and are not interchangeable.

Installing a wheel does not fetch the compiler on first use. Building from a source archive can fetch the compiler because platform directories are excluded from the archive.

## Build wheels

```bash
python -m build --wheel
```

The custom `scripts/hatch_build.py` hook selects the host target or `PYTSCHECK_BUILD_PLATFORM`, verifies the chosen binary, and includes only that target. On POSIX:

```bash
PYTSCHECK_BUILD_PLATFORM=win32-x64 python -m build --wheel
```

On PowerShell:

```powershell
$env:PYTSCHECK_BUILD_PLATFORM = "win32-x64"
python -m build --wheel
Remove-Item Env:PYTSCHECK_BUILD_PLATFORM
```

Cross-building packages an upstream binary; it does not compile Go or prove native execution on the target. All target identifiers are listed in [supported platforms](supported-platforms.md).

## CI artifacts

The **Build PyPI distributions** workflow uploads `wheel-<platform>` and `compiler-<platform>` artifacts for nine targets, plus `sdist`. Extract the wheel and source artifacts before uploading to PyPI. Compiler artifacts are for standalone tooling/downloads and must not be passed to Twine.

Preserve adjacent declaration files when using a compiler bundle directly. A bare executable can start but may not find required standard libraries. See [publishing](publishing.md) for the release procedure.
