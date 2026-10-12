"""Build self-contained, Python ABI independent, platform-specific wheels."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

TAGS = {
    "linux-x64": "manylinux_2_17_x86_64.manylinux2014_x86_64",
    "linux-arm64": "manylinux_2_17_aarch64.manylinux2014_aarch64",
    "win32-x64": "win_amd64",
    "win32-arm64": "win_arm64",
    "darwin-x64": "macosx_12_0_x86_64",
    "darwin-arm64": "macosx_12_0_arm64",
}


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        if self.target_name != "wheel" or version == "editable":
            return
        sys.path.insert(0, str(Path(self.root) / "scripts"))
        from build_binaries import BIN_ROOT, PLATFORMS, VERSION, fetch

        arch = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64"}.get(
            platform.machine().lower(), platform.machine().lower()
        )
        system = {"linux": "linux", "win32": "win32", "darwin": "darwin"}.get(sys.platform)
        target = os.environ.get("PYTSCHECK_BUILD_PLATFORM", f"{system}-{arch}")
        if target not in TAGS:
            raise ValueError(f"unsupported wheel platform: {target}")
        manifest_path = BIN_ROOT / "manifest.json"
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        entry = manifest.get("platforms", {}).get(target)
        dest = BIN_ROOT / PLATFORMS[target]
        if (
            entry is None
            or entry.get("version") != VERSION
            or not (dest / entry["binary_relpath"]).is_file()
        ):
            entry = fetch(target, BIN_ROOT)
        binary = dest / entry["binary_relpath"]
        actual = "sha512-" + base64.b64encode(hashlib.sha512(binary.read_bytes()).digest()).decode()
        if actual != entry.get("integrity"):
            raise ValueError(f"compiler checksum mismatch for {target}; fetch it again")
        wheel_manifest = Path(self.root) / "build" / f"manifest-{target}.json"
        wheel_manifest.parent.mkdir(parents=True, exist_ok=True)
        wheel_manifest.write_text(
            json.dumps({"compiler_version": VERSION, "platforms": {target: entry}}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        build_data["tag"] = f"py3-none-{TAGS[target]}"
        build_data["pure_python"] = False
        build_data["force_include"][str(dest)] = f"pytscheck/bin/{PLATFORMS[target]}"
        build_data["force_include"][str(wheel_manifest)] = "pytscheck/bin/manifest.json"
