"""PyTSCheck: Python-native TypeScript type checking.

PyTSCheck wraps Microsoft's native TypeScript 7 compiler (``tsgo``) and
exposes a typed Python API for checking source strings, files, and
projects. The compiler is bundled inside platform-specific wheels, so no
Node.js or Go installation is required.

Public API
----------

The top-level entry points mirror the module-level functions in
:mod:`pytscheck.api`::

    from pytscheck import check, check_file, check_project

    result = check('const age: number = "twenty";')
    if not result.success:
        for diagnostic in result.errors:
            print(diagnostic.file, diagnostic.line, diagnostic.message)

Adapter authors import from :mod:`pytscheck.adapters` instead; the core
package never imports a specific adapter.

Stability
---------

The names re-exported here are the public surface and follow Semantic
Versioning. Anything not listed in :data:`__all__` is internal and may
change without notice.

Importing this module is cheap and safe: no subprocess is launched, no
binary is located, and no network access occurs until a ``check*``
function is called. This matters for packaging tests that run on machines
without a bundled compiler.
"""

from __future__ import annotations

from .api import check, check_file, check_project
from .config import CompilerOptions
from .exceptions import (
    AdapterDiscoveryError,
    AdapterError,
    AdapterExtractionError,
    AdapterMappingError,
    AdapterProtocolError,
    AdapterRegistrationError,
    CompilerExecutionError,
    CompilerNotFoundError,
    CompilerTimeoutError,
    ConfigurationError,
    OutputParseError,
    PyTSCheckError,
    UnsupportedPlatformError,
)
from .models import Diagnostic, RelatedInformation, Result, SourceFile
from .version import ADAPTER_PROTOCOL_VERSION, COMPILER_VERSION, __version__

__all__ = [
    # Version metadata
    "__version__",
    "COMPILER_VERSION",
    "ADAPTER_PROTOCOL_VERSION",
    # Public API
    "check",
    "check_file",
    "check_project",
    # Configuration
    "CompilerOptions",
    # Models
    "Result",
    "Diagnostic",
    "RelatedInformation",
    "SourceFile",
    # Exceptions
    "PyTSCheckError",
    "UnsupportedPlatformError",
    "CompilerNotFoundError",
    "CompilerExecutionError",
    "CompilerTimeoutError",
    "OutputParseError",
    "ConfigurationError",
    "AdapterError",
    "AdapterDiscoveryError",
    "AdapterExtractionError",
    "AdapterMappingError",
    "AdapterProtocolError",
    "AdapterRegistrationError",
]