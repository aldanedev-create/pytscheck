#!/usr/bin/env python3
"""Re-verify on-disk binaries against bin/manifest.json."""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN_ROOT = REPO_ROOT / "src" / "pytscheck" / "bin"
MANIFEST_PATH = BIN_ROOT / "manifest.json"


def verify_platform(platform: str, entry: dict) -> bool:
    dest = (
        BIN_ROOT
        / {
            "win32-x64": "windows-amd64",
            "win32-arm64": "windows-arm64",
            "linux-x64": "linux-amd64",
            "linux-arm64": "linux-arm64",
            "linux-arm": "linux-arm",
            "linux-ia32": "linux-386",
            "win32-ia32": "windows-386",
            "darwin-x64": "darwin-amd64",
            "darwin-arm64": "darwin-arm64",
        }[platform]
    )

    binary = dest / entry["binary_relpath"]
    if not binary.exists():
        print(f"  MISSING binary: {binary}")
        return False
    print(f"  binary present: {binary} ({binary.stat().st_size:,} bytes)")

    actual = "sha512-" + base64.b64encode(hashlib.sha512(binary.read_bytes()).digest()).decode()
    if actual != entry.get("integrity") or binary.stat().st_size != entry.get("size_bytes"):
        print("  CHECKSUM/SIZE MISMATCH")
        return False

    # Count .d.ts files
    dts = list(dest.rglob("*.d.ts"))
    print(f"  .d.ts files: {len(dts)}")
    ok = bool(dts)

    # License / notice present?
    for name in ("LICENSE", "NOTICE.txt"):
        found = list(dest.rglob(name))
        print(f"  {name}: {'found' if found else 'MISSING'}")
        ok = ok and bool(found)

    return ok


def main() -> int:
    if not MANIFEST_PATH.exists():
        print(f"manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        return 1
    manifest = json.loads(MANIFEST_PATH.read_text())
    print(f"compiler_version: {manifest['compiler_version']}\n")
    ok = True
    for platform, entry in manifest["platforms"].items():
        print(f"[{platform}]")
        if not verify_platform(platform, entry):
            ok = False
        print()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
