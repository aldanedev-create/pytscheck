"""Fixtures for security tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


@pytest.fixture
def hostile_filenames() -> list[str]:
    """Filenames that could cause problems if unsanitized."""
    return [
        "..",
        "../escape",
        "../../escape",
        "..\\escape",
        "a/../../b",
        "/absolute",
        "C:\\absolute",
        "file\x00.ts",  # NUL byte
        "file\nnewline.ts",
        "file\rreturn.ts",
        "file\ttab.ts",
        "file;rm -rf.ts",
        "file$(whoami).ts",
        "file`whoami`.ts",
        "file|pipe.ts",
        "file&amp.ts",
        "file<.ts",
        "file>.ts",
        "file*.ts",
        "file?.ts",
        "file[abc].ts",
        "file{}.ts",
        "file~.ts",
        "file!.ts",
        "." * 300 + ".ts",  # very long
        "\u202e\u0000.ts",  # RTL override + NUL
    ]


@pytest.fixture
def hostile_source_snippets() -> list[str]:
    """Source snippets designed to stress the parser."""
    return [
        "// " + "x" * 100_000,
        "/* " + "*" * 100_000 + " */",
        "const x = " + "1 + " * 10_000 + "1;",
        'const s = "' + "a" * 500_000 + '";',
        "\x00\x01\x02\x03",
        "\ufeffconst x = 1;",  # BOM
        "const \u202ex = 1;",  # RTL override
        "const x = 1;\n" * 50_000,
    ]


@pytest.fixture
def hostile_json_payloads() -> list[str]:
    """Strings that stress the JSON parser."""
    return [
        "{" * 10_000 + "}" * 10_000,  # deeply nested
        "[" * 100_000 + "]" * 100_000,
        '{"a": ' + "1" * 1_000_000 + "}",  # huge number
        '{"a": "' + "x" * 1_000_000 + '"}',  # huge string
        "null",
        "true",
        '"a string"',
        "12345",
        "not json at all",
    ]


@pytest.fixture
def symlink_escape_setup(tmp_path: Path):
    """Set up a symlink that points outside tmp_path, for escape tests."""
    if sys.platform == "win32":
        pytest.skip("POSIX symlink semantics required")

    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir(exist_ok=True)
    (outside / "target.ts").write_text("export const x: number = 1;\n", encoding="utf-8")

    link = tmp_path / "link"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported")

    yield {"outside": outside, "link": link}
    # cleanup handled by tmp_path parent removal in most environments
