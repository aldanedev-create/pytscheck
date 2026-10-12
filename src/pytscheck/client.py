"""High-level client facade.

This is the seam where a future programmatic TypeScript API would slot in.
Today it delegates to the subprocess-based checker. Callers who want to
swap the backend can construct a Client with a different ``runner``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import api, checker
from .config import CompilerOptions
from .models import Result
from .runner import RunResult

RunnerFn = Callable[..., RunResult]


@dataclass
class Client:
    """Entry point for programmatic use.

    ``runner`` is injectable for testing; defaults to the real subprocess runner.
    """

    runner: RunnerFn | None = None

    def check(
        self,
        source: str,
        *,
        filename: str = "input.ts",
        options: CompilerOptions | None = None,
        keep_raw: bool = False,
    ) -> Result:
        with checker._use_runner(self.runner):
            return api.check(source, filename=filename, options=options, keep_raw=keep_raw)

    def check_file(
        self,
        path: str | Path,
        *,
        options: CompilerOptions | None = None,
        keep_raw: bool = False,
    ) -> Result:
        with checker._use_runner(self.runner):
            return api.check_file(path, options=options, keep_raw=keep_raw)

    def check_project(
        self,
        project_root: str | Path,
        *,
        options: CompilerOptions | None = None,
        keep_raw: bool = False,
    ) -> Result:
        with checker._use_runner(self.runner):
            return api.check_project(project_root, options=options, keep_raw=keep_raw)


__all__ = ["Client", "RunnerFn"]
