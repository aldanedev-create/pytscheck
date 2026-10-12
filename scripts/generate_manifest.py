#!/usr/bin/env python3
"""Regenerate src/pytscheck/bin/manifest.json from what's on disk.

Normally `build_binaries.py` writes the manifest as part of fetching the
pinned tarballs. This script is the exception path: when a developer has
placed a binary manually (say, an unreleased platform build) and wants the
manifest to reflect it.

It inspects each platform directory, computes the SHA-512 of the binary,
and writes a manifest entry. It does NOT fetch anything over the network.

Exit codes:

    0  success (or --dry-run shows no change)
    1  drift detected in --check mode
    2  usage error
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN_ROOT = REPO_ROOT / "src" / "pytscheck" / "bin"
MANIFEST_PATH = BIN_ROOT / "manifest.json"

sys.path.insert(0, str(REPO_ROOT / "src"))
try:
    from pytscheck.version import COMPILER_VERSION  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover
    print(f"error: cannot import pytscheck.version: {exc}", file=sys.stderr)
    raise SystemExit(2) from exc


# npm platform name -> bin/ directory
_PLATFORM_DIRS: dict[str, str] = {
    "win32-x64": "windows-amd64",
    "win32-arm64": "windows-arm64",
    "linux-x64": "linux-amd64",
    "linux-arm64": "linux-arm64",
    "darwin-x64": "darwin-amd64",
    "darwin-arm64": "darwin-arm64",
}


def _hash_file(path: Path) -> tuple[str, int]:
    """Return (integrity_string, size_bytes) using SHA-512."""
    h = hashlib.sha512()
    size = 0
    with path.open("rb") as fh:
        while chunk := fh.read(1024 * 1024):
            h.update(chunk)
            size += len(chunk)
    digest = base64.b64encode(h.digest()).decode("ascii")
    return f"sha512-{digest}", size


def _find_binary(platform_dir: Path) -> Path | None:
    """Locate the tsgo binary under a platform directory."""
    for name in ("tsgo", "tsgo.exe"):
        for candidate in platform_dir.rglob(name):
            if candidate.is_file():
                return candidate
    return None


def _scan_platform(platform_dir: Path) -> dict | None:
    """Return a manifest entry for one platform, or None if empty."""
    if not platform_dir.is_dir():
        return None
    binary = _find_binary(platform_dir)
    if binary is None:
        return None
    integrity, size = _hash_file(binary)
    rel = binary.relative_to(platform_dir).as_posix()
    return {
        "binary_relpath": rel,
        "integrity": integrity,
        "size_bytes": size,
    }


def build_manifest() -> dict:
    """Inspect disk and construct a manifest dict."""
    existing = _load_existing().get("platforms", {})
    platforms: dict[str, dict] = {}
    for npm_platform, dirname in _PLATFORM_DIRS.items():
        entry = _scan_platform(BIN_ROOT / dirname)
        if entry is None:
            continue
        entry = {
            "npm_platform": npm_platform,
            "version": COMPILER_VERSION,
            "binary_relpath": entry["binary_relpath"],
            "integrity": entry["integrity"],
            "size_bytes": entry["size_bytes"],
            # tarball is filled in by build_binaries.py; blank here
            "tarball": "",
        }
        old = existing.get(npm_platform, {})
        if old.get("integrity") == entry["integrity"]:
            entry["tarball"] = old.get("tarball", "")
            if "tarball_integrity" in old:
                entry["tarball_integrity"] = old["tarball_integrity"]
        platforms[npm_platform] = entry
    return {
        "compiler_version": COMPILER_VERSION,
        "platforms": platforms,
    }


def _load_existing() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _manifests_equal(a: dict, b: dict) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_manifest",
        description="Regenerate src/pytscheck/bin/manifest.json from disk.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the manifest to disk (default: dry-run)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the on-disk manifest matches; exit 1 on drift",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the constructed manifest as JSON to stdout",
    )
    args = parser.parse_args(argv)

    current = build_manifest()
    existing = _load_existing()

    if args.json:
        print(json.dumps(current, indent=2))
        return 0

    if args.check:
        if _manifests_equal(current, existing):
            print("OK: manifest is up to date")
            return 0
        print("DRIFT: manifest differs from disk contents")
        _print_diff(existing, current)
        return 1

    if _manifests_equal(current, existing):
        print("OK: manifest is already up to date")
        return 0

    if args.write:
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {MANIFEST_PATH}")
        return 0

    print("(dry-run) manifest would change:")
    _print_diff(existing, current)
    print("\nrun with --write to apply")
    return 0


def _print_diff(old: dict, new: dict) -> None:
    old_platforms = set(old.get("platforms", {}))
    new_platforms = set(new.get("platforms", {}))
    for p in sorted(new_platforms - old_platforms):
        print(f"  + {p}")
    for p in sorted(old_platforms - new_platforms):
        print(f"  - {p}")
    for p in sorted(old_platforms & new_platforms):
        if old["platforms"][p] != new["platforms"][p]:
            print(f"  ~ {p} (changed)")
    if old.get("compiler_version") != new.get("compiler_version"):
        print(
            f"  ~ compiler_version: {old.get('compiler_version')} -> {new.get('compiler_version')}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
