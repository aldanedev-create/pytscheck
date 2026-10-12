"""Tests that hostile filenames are handled safely."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck.exceptions import ConfigurationError, PyTSCheckError


def test_filename_with_null_byte_rejected(hostile_filenames) -> None:
    from pytscheck.api import check

    for name in hostile_filenames:
        if "\x00" in name:
            with pytest.raises(ConfigurationError, match="NUL"):
                check("const x = 1;", filename=name)


def test_filename_with_slash_rejected(hostile_filenames) -> None:
    from pytscheck.api import check

    for name in hostile_filenames:
        if "/" in name and "\x00" not in name:
            with pytest.raises(ConfigurationError):
                check("const x = 1;", filename=name)


def test_filename_with_backslash_rejected(hostile_filenames) -> None:
    from pytscheck.api import check

    for name in hostile_filenames:
        if "\\" in name and "\x00" not in name:
            with pytest.raises(ConfigurationError):
                check("const x = 1;", filename=name)


def test_safe_filenames_accepted(tsgo_binary) -> None:
    from pytscheck.api import check

    for name in ["input.ts", "app.tsx", "index.d.ts", "a-file.ts", "a_file.ts"]:
        r = check("const x: number = 1;", filename=name)
        assert isinstance(r.success, bool)


def test_empty_filename(tsgo_binary) -> None:
    from pytscheck.api import check

    with pytest.raises(ConfigurationError, match="non-empty basename"):
        check("const x: number = 1;", filename="")


def test_very_long_filename(tsgo_binary) -> None:
    from pytscheck.api import check

    name = "a" * 500 + ".ts"
    try:
        r = check("const x = 1;", filename=name)
    except PyTSCheckError:
        return
    assert isinstance(r.success, bool)


def test_filename_with_shell_metacharacters_rejected_or_safe(tsgo_binary) -> None:
    """Shell metacharacters in the filename must not be interpreted by a shell."""
    from pytscheck.api import check

    # These are all safe as long as no shell is involved
    for name in ["file;ls.ts", "file`whoami`.ts", "file$(ls).ts", "file|cat.ts"]:
        try:
            r = check("const x: number = 1;", filename=name)
        except (ConfigurationError, PyTSCheckError):
            continue
        assert isinstance(r.success, bool)


def test_filename_with_ampersand(tsgo_binary) -> None:
    from pytscheck.api import check

    r = check("const x: number = 1;", filename="file&amp.ts")
    assert isinstance(r.success, bool)


def test_filename_with_newline(tsgo_binary) -> None:
    from pytscheck.api import check

    try:
        r = check("const x: number = 1;", filename="file\nnewline.ts")
    except (ConfigurationError, PyTSCheckError):
        return
    assert isinstance(r.success, bool)


def test_file_with_hostile_name_on_disk(tsgo_binary, tmp_path: Path) -> None:
    """A file with shell metacharacters in its name must check cleanly."""
    from pytscheck import check_file

    f = tmp_path / "weird;name.ts"
    f.write_text("export const x: number = 1;\n", encoding="utf-8")
    r = check_file(f)
    assert r.success


def test_file_with_space_and_quote(tsgo_binary, tmp_path: Path) -> None:
    from pytscheck import check_file

    f = tmp_path / "a b'c\".ts"
    try:
        f.write_text("export const x: number = 1;\n", encoding="utf-8")
    except OSError:
        pytest.skip("filesystem rejects this filename")
    r = check_file(f)
    assert r.success
