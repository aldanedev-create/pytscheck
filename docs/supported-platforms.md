# Supported platforms

Choose a target matching the Python interpreter architecture. For example, x64 Python on an ARM Windows system requires the x64 wheel.

| OS / architecture | Build identifier | Bundled directory | Wheel platform tag |
| --- | --- | --- | --- |
| Linux x64 | `linux-x64` | `linux-amd64` | `manylinux_2_17_x86_64.manylinux2014_x86_64` |
| Linux ARM64 | `linux-arm64` | `linux-arm64` | `manylinux_2_17_aarch64.manylinux2014_aarch64` |
| Windows x64 | `win32-x64` | `windows-amd64` | `win_amd64` |
| Windows ARM64 | `win32-arm64` | `windows-arm64` | `win_arm64` |
| macOS Intel | `darwin-x64` | `darwin-amd64` | `macosx_12_0_x86_64` |
| macOS Apple Silicon | `darwin-arm64` | `darwin-arm64` | `macosx_12_0_arm64` |

Linux tags target glibc 2.17+. They are not musllinux wheels. macOS 12 is the minimum encoded by the bundled Mach-O binaries. Windows wheels contain `.exe` files; other wheels contain an executable `tsgo`.

The outer wheel tags start with `py3-none`; the package's Python metadata still requires Python 3.11+. There is no universal `any` wheel.

CI builds and verifies all six artifacts. Native Linux x64 tests and macOS/Windows runner tests do not establish native execution coverage for every architecture. Cross-building verifies packaging and checksums, not execution on another CPU.

See [binary distribution](binary-distribution.md) for build identifiers and [installation](installation.md) for selecting a wheel.
