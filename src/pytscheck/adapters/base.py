"""The compiler-agnostic adapter protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .sources import SourceFile


@runtime_checkable
class CompilerAdapter(Protocol):
    """Structural protocol implemented by every adapter.

    Implementations live in the consuming tool's package. pytscheck core
    never imports them directly; registration is via the entry-point group
    ``pytscheck.adapters``.
    """

    @property
    def name(self) -> str:
        """A short, unique identifier (e.g. ``"teloc"``)."""
        ...

    def get_sources(self, project_root: str) -> list[SourceFile]:
        """Return the TypeScript sources to check.

        Must raise :class:`AdapterExtractionError` (not return a diagnostic)
        if the tool cannot produce TypeScript for any input.
        """
        ...


__all__ = ["CompilerAdapter"]