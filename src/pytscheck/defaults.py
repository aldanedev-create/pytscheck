"""Default limits and constants. All tunable by callers."""

from __future__ import annotations

from typing import Final

# Subprocess
DEFAULT_TIMEOUT_SECONDS: Final[float] = 60.0
DEFAULT_MAX_STDOUT_BYTES: Final[int] = 32 * 1024 * 1024  # 32 MiB
DEFAULT_MAX_STDERR_BYTES: Final[int] = 4 * 1024 * 1024  # 4 MiB

# Inputs
DEFAULT_MAX_SOURCE_BYTES: Final[int] = 8 * 1024 * 1024  # 8 MiB
DEFAULT_MAX_FILES_PER_PROJECT: Final[int] = 20_000

# Project
TSCONFIG_FILENAME: Final[str] = "tsconfig.json"
TYPESCRIPT_EXTENSIONS: Final[frozenset[str]] = frozenset({".ts", ".tsx", ".mts", ".cts"})
DECLARATION_EXTENSIONS: Final[frozenset[str]] = frozenset({".d.ts"})

# Adapter
DEFAULT_ADAPTER_ENTRY_POINT_GROUP: Final[str] = "pytscheck.adapters"

__all__ = [
    "DECLARATION_EXTENSIONS",
    "DEFAULT_ADAPTER_ENTRY_POINT_GROUP",
    "DEFAULT_MAX_FILES_PER_PROJECT",
    "DEFAULT_MAX_SOURCE_BYTES",
    "DEFAULT_MAX_STDERR_BYTES",
    "DEFAULT_MAX_STDOUT_BYTES",
    "DEFAULT_TIMEOUT_SECONDS",
    "TSCONFIG_FILENAME",
    "TYPESCRIPT_EXTENSIONS",
]
