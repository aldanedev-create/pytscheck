"""Exception hierarchy for pytscheck.

Design rules:

- Every error raised by the library derives from :class:`PyTSCheckError`.
- Operational failures (missing binary, crash, timeout, unparsable output)
  are never reported as a successful check.
- Adapter extraction failures are :class:`AdapterError` subclasses, never
  diagnostics. This keeps a transpiler bug from being mistaken for a type error.
"""

from __future__ import annotations


class PyTSCheckError(Exception):
    """Base class for all pytscheck errors."""


class UnsupportedPlatformError(PyTSCheckError):
    """The current OS/architecture has no bundled tsgo binary."""


class CompilerNotFoundError(PyTSCheckError):
    """The bundled tsgo binary is missing or not executable."""


class CompilerExecutionError(PyTSCheckError):
    """tsgo crashed, failed to launch, or exited without parsable output.

    The process's ``returncode``, ``stdout``, and ``stderr`` (all optional)
    are attached for diagnostics. See :class:`CompilerTimeoutError` for the
    specific case of a timeout.
    """

    __slots__ = ("returncode", "stderr", "stdout")

    def __init__(
        self,
        message: str,
        *,
        returncode: int | None = None,
        stdout: str | None = None,
        stderr: str | None = None,
    ) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class CompilerTimeoutError(CompilerExecutionError):
    """tsgo exceeded the configured timeout."""

    __slots__ = ()


class OutputParseError(PyTSCheckError):
    """tsgo output could not be parsed into diagnostics."""

    __slots__ = ("raw_output",)

    def __init__(self, message: str, *, raw_output: str | None = None) -> None:
        super().__init__(message)
        self.raw_output = raw_output


class ConfigurationError(PyTSCheckError):
    """Bad tsconfig, compiler options, or invalid caller input."""


# --- Adapter layer ---------------------------------------------------------


class AdapterError(PyTSCheckError):
    """Base class for adapter-layer failures."""


class AdapterRegistrationError(AdapterError):
    """An adapter could not be registered (duplicate name, bad shape)."""


class AdapterDiscoveryError(AdapterError):
    """Entry-point discovery failed for one or more adapters."""


class AdapterExtractionError(AdapterError):
    """The adapter could not produce TypeScript from its source.

    This is *not* a type error and must never be reported as one.
    """


class AdapterMappingError(AdapterError):
    """Source-map parsing or diagnostic remapping failed."""


class AdapterProtocolError(AdapterError):
    """The adapter does not satisfy the required protocol."""


__all__ = [
    "AdapterDiscoveryError",
    "AdapterError",
    "AdapterExtractionError",
    "AdapterMappingError",
    "AdapterProtocolError",
    "AdapterRegistrationError",
    "CompilerExecutionError",
    "CompilerNotFoundError",
    "CompilerTimeoutError",
    "ConfigurationError",
    "OutputParseError",
    "PyTSCheckError",
    "UnsupportedPlatformError",
]
