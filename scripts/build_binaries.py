#!/usr/bin/env python3
"""Fetch pinned tsgo binaries from npm, verify SHA-512, extract safely."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
import tarfile
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
    "darwin-x64": "darwin-amd64",
    "darwin-arm64": "darwin-arm64",
}

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


def fetch(platform: str, out_root: Path) -> dict:
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
