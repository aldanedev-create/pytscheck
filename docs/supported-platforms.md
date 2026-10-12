# Supported platforms

Each wheel includes the native compiler, TypeScript libraries, and upstream notices for one platform. No Node.js installation is needed at runtime.

| Operating system | Architecture | Bundle directory | Wheel platform |
| --- | --- | --- | --- |
| Linux (glibc 2.17+) | x86-64 | linux-amd64 | manylinux_2_17_x86_64 |
| Linux (glibc 2.17+) | ARM64 | linux-arm64 | manylinux_2_17_aarch64 |
| Windows | x86-64 | windows-amd64 | win_amd64 |
| Windows | ARM64 | windows-arm64 | win_arm64 |
| macOS 12+ | Intel | darwin-amd64 | macosx_12_0_x86_64 |
| macOS 12+ | Apple Silicon | darwin-arm64 | macosx_12_0_arm64 |

Source builds download the pinned compiler from npm and verify its SHA-512 integrity. For offline builds, fetch it first with `python scripts/build_binaries.py <npm-platform>` and retain the manifest and platform directory. To build for another platform, set `PYTSCHECK_BUILD_PLATFORM` to `linux-x64`, `linux-arm64`, `win32-x64`, `win32-arm64`, `darwin-x64`, or `darwin-arm64`.
