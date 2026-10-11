"""Protocol-version and capability compatibility checks."""

from __future__ import annotations

from ..version import ADAPTER_PROTOCOL_VERSION
from .base import CompilerAdapter
from .errors import AdapterProtocolError


def check_protocol_version(adapter: CompilerAdapter) -> None:
    """Verify the adapter declares a compatible protocol version.

    Adapters may expose ``protocol_version`` (a string). If absent, we assume
    "1.x" compatibility and accept.
    """
    declared = getattr(adapter, "protocol_version", None)
    if declared is None:
        return
    if not isinstance(declared, str):
        raise AdapterProtocolError(
            f"adapter {adapter.name!r} has non-string protocol_version"
        )
    if declared.split(".")[0] != ADAPTER_PROTOCOL_VERSION.split(".")[0]:
        raise AdapterProtocolError(
            f"adapter {adapter.name!r} speaks protocol {declared}, "
            f"core speaks {ADAPTER_PROTOCOL_VERSION}"
        )


__all__ = ["check_protocol_version"]