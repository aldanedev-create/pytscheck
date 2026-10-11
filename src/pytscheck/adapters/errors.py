"""Adapter-layer exceptions.

Re-exported from the top-level exception hierarchy so callers can catch
``pytscheck.AdapterError`` without knowing about this submodule.
"""

from __future__ import annotations

from ..exceptions import (
    AdapterDiscoveryError,
    AdapterError,
    AdapterExtractionError,
    AdapterMappingError,
    AdapterProtocolError,
    AdapterRegistrationError,
)

__all__ = [
    "AdapterError",
    "AdapterDiscoveryError",
    "AdapterExtractionError",
    "AdapterMappingError",
    "AdapterProtocolError",
    "AdapterRegistrationError",
]