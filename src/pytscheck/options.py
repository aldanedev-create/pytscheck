"""Translate :class:`CompilerOptions` into tsgo command-line arguments."""

from __future__ import annotations

from .config import CompilerOptions
from .paths import assert_no_null_bytes


def options_to_argv(options: CompilerOptions) -> list[str]:
    """Convert compiler options into an argv fragment (no shell quoting)."""
    argv: list[str] = []

    if options.no_emit:
        argv.append("--noEmit")
    if options.strict:
        argv.append("--strict")
    if options.skip_lib_check:
        argv.append("--skipLibCheck")

    for names, flag in ((options.types, "--types"), (options.lib, "--lib")):
        if names:
            for name in names:
                assert_no_null_bytes(name, what=f"{flag} name")
            argv += [flag, ",".join(names)]
    if options.target is not None:
        assert_no_null_bytes(options.target, what="target")
        argv += ["--target", options.target]
    if options.module is not None:
        assert_no_null_bytes(options.module, what="module")
        argv += ["--module", options.module]
    if options.module_resolution is not None:
        assert_no_null_bytes(options.module_resolution, what="moduleResolution")
        argv += ["--moduleResolution", options.module_resolution]

    # Free-form extras: keys must be bare flags or --key value pairs.
    for key, value in options.extra.items():
        assert_no_null_bytes(key, what="extra option key")
        flag = key if key.startswith("--") else f"--{key}"
        if value is True:
            argv.append(flag)
        elif value is False or value is None:
            continue
        else:
            assert_no_null_bytes(str(value), what=f"value for {key}")
            argv += [flag, str(value)]

    return argv


__all__ = ["options_to_argv"]
