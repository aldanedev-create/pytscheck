#!/usr/bin/env python3
"""Fetch pinned tsgo binaries from npm, verify SHA-512, extract safely."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

REGISTRY = "https://registry.npmjs.org/"

# Pin exactly. Confirmed latest tag as of Phase 0:
# https://www.npmjs.com/package/@typescript/native-preview
VERSION = "7.0.0-dev.20260707.2"

# npm platform  ->  bin/ folder
PLATFORMS: dict[str, str] = {
    "win32-x64": "windows-amd64",
    "win32-arm64": "windows-arm64",
    "linux-x64": "linux-amd64",
    "linux-arm64": "linux-arm64",
    "linux-arm": "linux-arm",
    "linux-ia32": "linux-386",
    "win32-ia32": "windows-386",
    "darwin-x64": "darwin-amd64",
    "darwin-arm64": "darwin-arm64",
}

SOURCE_TARGETS = {"linux-ia32": "linux", "win32-ia32": "windows"}
SOURCE_COMMIT = "9977d6d38fcc78de8ae71770f3aa08256e6cc861"
SOURCE_REPOSITORY = "https://github.com/microsoft/typescript-go.git"
SOURCE_GO_VERSION = "go1.26.9"

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN_ROOT = REPO_ROOT / "src" / "pytscheck" / "bin"
MANIFEST_PATH = BIN_ROOT / "manifest.json"

# Python 3.11 compatibility: tarfile filter= is 3.12+
_EXTRACT_KW: dict = {"filter": "data"} if sys.version_info >= (3, 12) else {}


def _npm_pkg(platform: str) -> str:
    # URL-encode the leading @typescript/ scope
    return f"@typescript%2Fnative-preview-{platform}"


def _fetch_metadata(platform: str) -> dict:
    url = f"{REGISTRY}{_npm_pkg(platform)}/{VERSION}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read())


def _download_tarball(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=300) as resp:
        return resp.read()


def _verify_integrity(data: bytes, integrity: str) -> None:
    algo, expected_b64 = integrity.split("-", 1)
    digest = hashlib.new(algo, data).digest()
    actual_b64 = base64.b64encode(digest).decode()
    if actual_b64 != expected_b64:
        raise RuntimeError(f"checksum mismatch: expected {expected_b64!r}, got {actual_b64!r}")


def _safe_extract(tar_bytes: bytes, dest: Path) -> None:
    """Extract only regular files under package/ into dest, stripping prefix."""
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:*") as tar:
        members = []
        for m in tar.getmembers():
            if not m.isfile():
                continue
            if not m.name.startswith("package/"):
                continue
            # Reject any traversal just in case
            clean = m.name[len("package/") :]
            if ".." in clean.split("/") or clean.startswith("/"):
                raise RuntimeError(f"unsafe member path: {m.name!r}")
            m.name = clean
            members.append(m)
        tar.extractall(dest, members=members, **_EXTRACT_KW)


def _fetch_npm(platform: str, out_root: Path) -> dict:
    """Download, verify, extract one platform. Returns manifest entry."""
    meta = _fetch_metadata(platform)["dist"]
    tarball_url: str = meta["tarball"]
    integrity: str = meta["integrity"]

    print(f"[{platform}] downloading {tarball_url}")
    data = _download_tarball(tarball_url)
    _verify_integrity(data, integrity)
    print(f"[{platform}] integrity OK ({len(data):,} bytes)")

    dest = out_root / PLATFORMS[platform]
    if dest.exists():
        import shutil

        shutil.rmtree(dest)
    _safe_extract(data, dest)

    exe_name = "tsgo.exe" if platform.startswith("win32") else "tsgo"
    exe = dest / "lib" / exe_name
    if not exe.exists():
        # Fallback: search for the binary anywhere
        candidates = list(dest.rglob(exe_name))
        if not candidates:
            raise RuntimeError(f"{exe_name} not found under {dest}")
        exe = candidates[0]
        print(f"[{platform}] binary found at non-standard path: {exe.relative_to(dest)}")

    if not platform.startswith("win32"):
        exe.chmod(0o755)

    return {
        "npm_platform": platform,
        "version": VERSION,
        "integrity": "sha512-"
        + base64.b64encode(hashlib.sha512(exe.read_bytes()).digest()).decode(),
        "tarball_integrity": integrity,
        "size_bytes": exe.stat().st_size,
        "tarball": tarball_url,
        "binary_relpath": str(exe.relative_to(dest)),
    }


def verify_static_linux(binary: Path, target: str) -> None:
    """Verify ELF CPU and absence of a dynamic loader before claiming musl support."""
    expected = {
        "linux-x64": (2, 62),
        "linux-arm64": (2, 183),
        "linux-arm": (1, 40),
        "linux-ia32": (1, 3),
    }[target]
    with binary.open("rb") as reader:
        header = reader.read(64)
        if len(header) < 52 or header[:4] != b"\x7fELF" or header[5] not in (1, 2):
            raise RuntimeError("Linux compiler is not a valid ELF executable")
        endian = "<" if header[5] == 1 else ">"
        machine = struct.unpack_from(endian + "H", header, 18)[0]
        if (header[4], machine) != expected:
            raise RuntimeError(f"Linux compiler CPU does not match {target}")
        if header[4] == 2:
            offset = struct.unpack_from(endian + "Q", header, 32)[0]
            width, count = struct.unpack_from(endian + "HH", header, 54)
        else:
            offset = struct.unpack_from(endian + "I", header, 28)[0]
            width, count = struct.unpack_from(endian + "HH", header, 42)
        if width < 4 or count == 0 or offset + width * count > binary.stat().st_size:
            raise RuntimeError("invalid ELF program header table")
        for index in range(count):
            reader.seek(offset + width * index)
            kind = struct.unpack(endian + "I", reader.read(4))[0]
            if kind in (2, 3):
                raise RuntimeError("musllinux wheels require a fully static compiler")


def _fetch_source(platform: str, out_root: Path) -> dict:
    """Build unpublished x86 targets from the exact npm release's source commit."""
    go = shutil.which("go")
    if go is None or shutil.which("git") is None:
        raise RuntimeError(f"building {platform} requires Git and Go {SOURCE_GO_VERSION}")
    version = subprocess.check_output([go, "version"], text=True).split()
    if len(version) < 3 or version[2] != SOURCE_GO_VERSION:
        raise RuntimeError(f"building {platform} requires Go {SOURCE_GO_VERSION}")
    base = "win32-x64" if platform.startswith("win32") else "linux-x64"
    if _fetch_metadata(base).get("gitHead") != SOURCE_COMMIT:
        raise RuntimeError("pinned npm compiler source commit differs from build configuration")
    out_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".tsgo-source-", dir=out_root) as temporary:
        staging = Path(temporary)
        entry = _fetch_npm(base, staging)
        package = staging / PLATFORMS[base]
        source = staging / "source"
        source.mkdir()
        for args in (
            ["init"],
            ["remote", "add", "origin", SOURCE_REPOSITORY],
            ["fetch", "--depth=1", "origin", SOURCE_COMMIT],
            ["checkout", "--detach", "FETCH_HEAD"],
        ):
            subprocess.run(["git", *args], cwd=source, check=True)
        actual = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=source, text=True
        ).strip()
        if actual != SOURCE_COMMIT:
            raise RuntimeError("source checkout does not match pinned commit")
        binary = package / entry["binary_relpath"]
        env = {
            **os.environ,
            "GOOS": SOURCE_TARGETS[platform],
            "GOARCH": "386",
            "GO386": "sse2",
            "CGO_ENABLED": "0",
            "GOTOOLCHAIN": "local",
            "GOWORK": "off",
            "GOFLAGS": "",
            "GOEXPERIMENT": "",
        }
        subprocess.run(
            [
                go,
                "build",
                "-mod=readonly",
                "-buildvcs=false",
                "-tags",
                "noembed",
                "-trimpath",
                "-ldflags",
                f"-s -w -X github.com/microsoft/typescript-go/internal/core.version={VERSION}",
                "-o",
                str(binary.resolve()),
                "./cmd/tsgo",
            ],
            cwd=source,
            env=env,
            check=True,
        )
        if platform.startswith("linux"):
            binary.chmod(0o755)
            verify_static_linux(binary, platform)
        metadata = json.loads((package / "package.json").read_text())
        metadata.update(name=f"pytscheck-tsgo-{platform}", cpu=["ia32"])
        (package / "package.json").write_text(json.dumps(metadata, indent=2) + "\n")
        entry.update(
            npm_platform=platform,
            integrity="sha512-"
            + base64.b64encode(hashlib.sha512(binary.read_bytes()).digest()).decode(),
            size_bytes=binary.stat().st_size,
            source_commit=SOURCE_COMMIT,
            source_repository=SOURCE_REPOSITORY,
            go_version=SOURCE_GO_VERSION,
            libraries_platform=base,
        )
        destination = out_root / PLATFORMS[platform]
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(package), destination)
        return entry


def fetch(platform: str, out_root: Path) -> dict:
    entry = (_fetch_source if platform in SOURCE_TARGETS else _fetch_npm)(platform, out_root)
    if platform.startswith("linux-"):
        verify_static_linux(out_root / PLATFORMS[platform] / entry["binary_relpath"], platform)
    return entry


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    targets = argv or list(PLATFORMS.keys())

    manifest: dict = {"compiler_version": VERSION, "platforms": {}}
    if MANIFEST_PATH.exists():
        existing = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if existing.get("compiler_version") == VERSION:
            for platform, entry in existing.get("platforms", {}).items():
                if (
                    platform in PLATFORMS
                    and (BIN_ROOT / PLATFORMS[platform] / entry["binary_relpath"]).is_file()
                ):
                    manifest["platforms"][platform] = entry
    for platform in targets:
        if platform not in PLATFORMS:
            print(f"unknown platform: {platform}", file=sys.stderr)
            return 2
        manifest["platforms"][platform] = fetch(platform, BIN_ROOT)

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nmanifest written: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
