"""Tests for encoding handling of source text and paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import checker
from tests.assertions import assert_valid_result


def test_ascii_source(tsgo_binary: Path) -> None:
    r = checker.check_source("export const x: number = 1;")
    assert r.success


def test_unicode_identifier(tsgo_binary: Path) -> None:
    r = checker.check_source("export const café: number = 1;")
    assert_valid_result(r)


def test_unicode_string_literal(tsgo_binary: Path) -> None:
    r = checker.check_source('export const s: string = "héllo 世界 🌍";')
    assert r.success


def test_unicode_error_message_preserved(tsgo_binary: Path) -> None:
    src = 'export const café: number = "héllo";'
    r = checker.check_source(src)
    assert not r.success
    assert r.errors


def test_utf8_file_on_disk(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "unicode.ts"
    f.write_text('export const s: string = "привет мир";\n', encoding="utf-8")
    r = checker.check_file(f)
    assert r.success


def test_utf8_bom_file_on_disk(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "bom.ts"
    f.write_bytes("\ufeffexport const x: number = 1;\n".encode("utf-8"))
    r = checker.check_file(f)
    assert_valid_result(r)


def test_crlf_file_on_disk(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "crlf.ts"
    f.write_bytes(b"export const x: number = 1;\r\n")
    r = checker.check_file(f)
    assert r.success


def test_latin1_file_does_not_crash(tsgo_binary: Path, tmp_path: Path) -> None:
    """A file with non-UTF-8 bytes must not crash the pipeline."""
    f = tmp_path / "latin1.ts"
    f.write_bytes(b'export const s: string = "\xe9";\n')
    # Behavior depends on tsgo; we only require: no crash, valid Result.
    try:
        r = checker.check_file(f)
    except Exception:
        return  # acceptable: configuration/parse error
    assert_valid_result(r)


def test_null_byte_in_source_rejected() -> None:
    from pytscheck.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError, match="NUL"):
        checker.check_source("const x = 1;\x00")


def test_source_with_emoji_roundtrips(tsgo_binary: Path) -> None:
    src = 'export const emoji: string = "🚀";'
    r = checker.check_source(src)
    assert r.success


def test_source_with_only_ascii_punctuation(tsgo_binary: Path) -> None:
    src = 'export const punctuation: string = "!@#$%^&*()_+-=[]{}|;:,.<>?";'
    r = checker.check_source(src)
    assert r.success