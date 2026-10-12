# Supported platforms

Choose a target matching the Python interpreter architecture. For example, x64 Python on an ARM Windows system requires the x64 wheel.

| OS / architecture | Build identifier | Bundled directory | Wheel platform tag |
| --- | --- | --- | --- |
| Linux x64 | `linux-x64` | `linux-amd64` | `manylinux_2_17_x86_64.manylinux2014_x86_64.musllinux_1_2_x86_64` |
| Linux ARM64 | `linux-arm64` | `linux-arm64` | `manylinux_2_17_aarch64.manylinux2014_aarch64.musllinux_1_2_aarch64` |
| Linux ARMv7 (32-bit) | `linux-arm` | `linux-arm` | `manylinux_2_17_armv7l.manylinux2014_armv7l.musllinux_1_2_armv7l` |
| Linux x86 (32-bit, SSE2) | `linux-ia32` | `linux-386` | `manylinux_2_17_i686.manylinux2014_i686.musllinux_1_2_i686` |
| Windows x86 (32-bit) | `win32-ia32` | `windows-386` | `win32` |
| Windows x64 | `win32-x64` | `windows-amd64` | `win_amd64` |
| Windows ARM64 | `win32-arm64` | `windows-arm64` | `win_arm64` |
| macOS Intel | `darwin-x64` | `darwin-amd64` | `macosx_12_0_x86_64` |
| macOS Apple Silicon | `darwin-arm64` | `darwin-arm64` | `macosx_12_0_arm64` |

Linux wheels carry combined glibc 2.17+ and musl 1.2+ tags. The same fully static Go executable runs with either libc; the build checks its ELF architecture and rejects dynamic dependencies before assigning these tags. Alpine is covered by the musllinux tags. macOS 12 is the minimum encoded by the bundled Mach-O binaries. Windows wheels contain `.exe` files; other wheels contain an executable `tsgo`.

The outer wheel tags start with `py3-none`; the package's Python metadata still requires Python 3.11+. There is no universal `any` wheel.

CI builds nine wheels. Runtime jobs install the actual wheels and check the compiler, JSDoc, projects, adapters, and source maps in Alpine x64/ARM64/ARMv7/x86 and glibc ARMv7/x86 containers. ARM and x86 containers use QEMU when needed, so these are execution tests under emulation rather than physical-device validation. Windows x86 uses real 32-bit Python on a Windows runner. Existing native macOS and Windows jobs continue to run.

See [binary distribution](binary-distribution.md) for build identifiers and [installation](installation.md) for selecting a wheel.

## Compiler provenance and build requirements

Linux ARMv7 uses the official pinned `native-preview-linux-arm` archive (upstream Go ARMv6 binary, runnable on ARMv7). Upstream does not publish x86 archives. Linux and Windows x86 are built without compiler-source modifications from commit `9977d6d38fcc78de8ae71770f3aa08256e6cc861`, the `gitHead` of compiler `7.0.0-dev.20260707.2`, using Go `1.26.9`, `GOARCH=386`, `GO386=sse2`, and `CGO_ENABLED=0`. Libraries and notices come from the matching pinned official archive. These x86 executables are PyTSCheck builds, not official upstream x86 releases. Their SHA-512, source commit, and toolchain are recorded in the manifest.

Building x86 wheels from a source checkout requires Git and Go 1.26.9; installing the finished wheels requires neither Go nor Node. `scripts/publish.py` builds all nine targets and therefore also requires those build tools. All source builds use the fixed commit rather than upstream main.

32-bit selection follows the Python interpreter's pointer width even when the operating system reports an x64/ARM64 CPU. Linux and Windows x86 require SSE2; legacy non-SSE2 x86, ARMv5/ARMv6 wheel tags, and 32-bit macOS are outside this support matrix.
