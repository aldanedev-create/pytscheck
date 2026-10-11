"""Version constants for pytscheck and its bundled compiler."""

from __future__ import annotations

__version__ = "0.1.0.dev0"

# Pinned bundled compiler. Must match src/pytscheck/bin/manifest.json.
COMPILER_VERSION = "7.0.0-dev.20260707.2"

# Adapter protocol version. Bump on breaking protocol changes.
ADAPTER_PROTOCOL_VERSION = "1.0"

__all__ = ["__version__", "COMPILER_VERSION", "ADAPTER_PROTOCOL_VERSION"]