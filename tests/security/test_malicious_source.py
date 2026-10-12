"""Tests for hostile TypeScript source input."""

from __future__ import annotations

from pathlib import Path

import pytest

from pytscheck import check, check_file
from pytscheck.exceptions import PyTSCheckError


def test_null_byte_in_source_rejected() -> None:
    from pytscheck.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError, match="NUL"):
        check("const x = 1;\x00")


def test_null_byte_first_char_rejected() -> None:
    from pytscheck.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError, match="NUL"):
        check("\x00const x = 1;")


def test_null_byte_in_file_rejected(tsgo_binary: Path, tmp_path: Path) -> None:
    from pytscheck.exceptions import ConfigurationError

    f = tmp_path / "null.ts"
    f.write_bytes(b"const x = 1;\x00")
    with pytest.raises((ConfigurationError, PyTSCheckError)):
        check_file(f)


def test_very_long_line(tsgo_binary: Path) -> None:
    src = 'const s: string = "' + "a" * 1_000_000 + '";'
    try:
        r = check(src)
    except PyTSCheckError:
        return  # acceptable: size limit reached
    assert r.success or not r.success  # no crash


def test_very_many_lines(tsgo_binary: Path) -> None:
    src = "const x = 1;\n" * 20_000
    try:
        r = check(src)
    except PyTSCheckError:
        return
    assert r.success or not r.success


def test_binary_content(tsgo_binary: Path, tmp_path: Path) -> None:
    f = tmp_path / "binary.ts"
    f.write_bytes(bytes(range(256)) * 100)
    try:
        r = check_file(f)
    except PyTSCheckError:
        return
    # A binary file is likely to produce syntax errors, not a crash.
    assert not r.success


def test_bom_at_start(tsgo_binary: Path) -> None:
    src = "\ufeffconst x: number = 1;"
    r = check(src)
    # BOM should be tolerated or produce a clean error
    assert isinstance(r.success, bool)


def test_rtl_override_in_identifier(tsgo_binary: Path) -> None:
    src = "const \u202ex: number = 1;"
    r = check(src)
    # No crash; success or diagnostic is fine
    assert isinstance(r.success, bool)


def test_zero_width_joiner_in_identifier(tsgo_binary: Path) -> None:
    src = "const a\u200db: number = 1;"
    r = check(src)
    assert isinstance(r.success, bool)


def test_deeply_nested_braces(tsgo_binary: Path) -> None:
    src = "const x = " + "(" * 5000 + "1" + ")" * 5000 + ";"
    try:
        r = check(src)
    except PyTSCheckError:
        return
    assert isinstance(r.success, bool)


def test_deeply_nested_arrays(tsgo_binary: Path) -> None:
    src = "const x: number[][][][] = [[[[]]]];"
    r = check(src)
    assert isinstance(r.success, bool)


def test_gigantic_type(tsgo_binary: Path) -> None:
    # A huge union type
    members = " | ".join(f"'{i}'" for i in range(5_000))
    src = f"type U = {members};\nexport const u: U = '42';\n"
    try:
        r = check(src)
    except PyTSCheckError:
        return
    assert isinstance(r.success, bool)


def test_source_with_only_control_chars(tsgo_binary: Path) -> None:
    src = "".join(chr(i) for i in range(1, 32))
    r = check(src)
    assert isinstance(r.success, bool)


def test_source_with_only_high_unicode(tsgo_binary: Path) -> None:
    src = "".join(chr(i) for i in range(0x1F600, 0x1F650))
    r = check(src)
    assert isinstance(r.success, bool)


def test_comment_with_nested_block_markers(tsgo_binary: Path) -> None:
    src = "/* start /* nested */ still in comment? */ const x = 1;"
    r = check(src)
    assert isinstance(r.success, bool)


def test_regex_with_slashes(tsgo_binary: Path) -> None:
    src = r"const re: RegExp = /\/path\/to\/file/;"
    r = check(src)
    assert isinstance(r.success, bool)


def test_string_with_backslash_escapes(tsgo_binary: Path) -> None:
    src = r'const s: string = "line1\nline2\ttab\\slash";'
    r = check(src)
    assert isinstance(r.success, bool)


def test_unterminated_string(tsgo_binary: Path) -> None:
    src = 'const s: string = "unterminated'
    r = check(src)
    assert not r.success


def test_unterminated_comment(tsgo_binary: Path) -> None:
    src = "/* never closed"
    r = check(src)
    assert not r.success


def test_unterminated_template_literal(tsgo_binary: Path) -> None:
    src = "const s = `unterminated"
    r = check(src)
    assert not r.success
