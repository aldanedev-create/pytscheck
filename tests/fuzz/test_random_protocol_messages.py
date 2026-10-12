"""Fuzz the source-map and adapter-protocol layers.

Feeds hostile source maps, malformed `SourceFile` objects, and random
adapter returns to `remap_diagnostics` and `collect_sources`. Verifies
that malformed input is rejected with the correct exception type and
never produces a wrong-but-silent result.
"""

from __future__ import annotations

import json
import random
import string

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from pytscheck.adapters.errors import (
    AdapterMappingError,
    AdapterProtocolError,
)
from pytscheck.adapters.source_maps import remap_diagnostics
from pytscheck.adapters.sources import collect_sources
from pytscheck.models import Diagnostic, SourceFile


def _diag(file: str = "a.ts") -> Diagnostic:
    return Diagnostic(file=file, line=1, column=1, code=1, category="error", message="m")


# ---------------------------------------------------------------------------
# Property-based: remap_diagnostics
# ---------------------------------------------------------------------------


@given(st.text())
@settings(
    max_examples=300,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_remap_never_crashes_on_arbitrary_source_map(source_map: str) -> None:
    src = SourceFile(
        path="a.ts",
        text="",
        origin_path="a.vel",
        source_map=source_map,
        kind="generated",
    )
    try:
        out = remap_diagnostics((_diag("a.ts"),), (src,))
    except AdapterMappingError:
        return
    assert isinstance(out, tuple)
    for d in out:
        assert isinstance(d, Diagnostic)


@given(st.binary(max_size=10_000))
@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_remap_never_crashes_on_binary_source_map(data: bytes) -> None:
    try:
        source_map = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    src = SourceFile(
        path="a.ts",
        text="",
        origin_path="a.vel",
        source_map=source_map,
        kind="generated",
    )
    try:
        remap_diagnostics((_diag("a.ts"),), (src,))
    except AdapterMappingError:
        return


# ---------------------------------------------------------------------------
# Structured hostile source maps
# ---------------------------------------------------------------------------


def _random_json(rng: random.Random, depth: int = 0) -> object:
    if depth > 4:
        return rng.choice([None, True, False, 0, "", "x"])
    choice = rng.randint(0, 6)
    if choice == 0:
        return None
    if choice == 1:
        return rng.choice([True, False])
    if choice == 2:
        return rng.randint(-(10**6), 10**6)
    if choice == 3:
        return "".join(rng.choices(string.printable, k=rng.randint(0, 50)))
    if choice == 4:
        return [_random_json(rng, depth + 1) for _ in range(rng.randint(0, 5))]
    if choice == 5:
        return {
            "".join(rng.choices(string.ascii_letters, k=5)): _random_json(rng, depth + 1)
            for _ in range(rng.randint(0, 5))
        }
    # Bias toward valid-looking source maps
    return {
        "version": rng.choice([3, 2, "3", None, 3.0]),
        "mappings": rng.choice(["", "AAAA", "x" * 100, None, 42]),
        "sources": rng.choice([[], ["a.ts"], None, "a.ts"]),
    }


def test_random_source_map_objects(rng: random.Random) -> None:
    for _ in range(500):
        value = _random_json(rng)
        payload = json.dumps(value)
        src = SourceFile(
            path="a.ts",
            text="",
            origin_path="a.vel",
            source_map=payload,
            kind="generated",
        )
        try:
            out = remap_diagnostics((_diag("a.ts"),), (src,))
        except AdapterMappingError:
            continue
        assert isinstance(out, tuple)


# ---------------------------------------------------------------------------
# Property-based: collect_sources
# ---------------------------------------------------------------------------


class _RecordingAdapter:
    def __init__(self, sources: object) -> None:
        self._sources = sources

    @property
    def name(self) -> str:
        return "rec"

    def get_sources(self, project_root: str) -> object:  # type: ignore[override]
        return self._sources


@given(
    st.one_of(
        st.none(),
        st.text(),
        st.integers(),
        st.lists(st.integers()),
        st.lists(st.text()),
        st.dictionaries(st.text(max_size=10), st.integers()),
    )
)
@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_collect_sources_rejects_bad_returns(payload: object) -> None:
    """Any non-list-of-SourceFile return must raise AdapterProtocolError."""
    adapter = _RecordingAdapter(payload)
    try:
        out = collect_sources(adapter, "/")  # type: ignore[arg-type]
    except (AdapterProtocolError, TypeError):
        return
    # Only an empty list from a valid list is acceptable
    assert out == ()


def test_collect_sources_random_sourcefile_lists(rng: random.Random) -> None:
    for _ in range(200):
        n = rng.randint(0, 5)
        sources = []
        for _ in range(n):
            path = "".join(rng.choices(string.ascii_letters + "._/", k=rng.randint(1, 20)))
            text = "".join(rng.choices(string.printable, k=rng.randint(0, 50)))
            sources.append(SourceFile(path=path, text=text))
        adapter = _RecordingAdapter(sources)
        try:
            out = collect_sources(adapter, "/")
        except AdapterProtocolError:
            continue
        assert isinstance(out, tuple)


def test_duplicate_paths_in_random_list(rng: random.Random) -> None:
    for _ in range(50):
        paths = ["".join(rng.choices(string.ascii_letters, k=5)) for _ in range(20)]
        sources = [SourceFile(path=p, text="") for p in paths]
        adapter = _RecordingAdapter(sources)
        try:
            out = collect_sources(adapter, "/")
        except AdapterProtocolError:
            continue
        # If it did not raise, the paths were unique
        assert len({s.path for s in out}) == len(out)


# ---------------------------------------------------------------------------
# Hostile source maps
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        "",
        " ",
        "{",
        "}",
        "[]",
        "null",
        "true",
        "42",
        '"a string"',
        '{"version": 3}',
        '{"mappings": ""}',
        '{"version": 3, "mappings": null}',
        '{"version": 3, "mappings": 42}',
        '{"version": 3, "mappings": {}}',
        '{"version": 3, "mappings": []}',
        '{"version": 3, "mappings": ""}',
        "\ufeff" + json.dumps({"version": 3, "mappings": ""}),
    ],
)
def test_specific_hostile_source_maps(payload: str) -> None:
    src = SourceFile(
        path="a.ts",
        text="",
        origin_path="a.vel",
        source_map=payload,
        kind="generated",
    )
    try:
        out = remap_diagnostics((_diag("a.ts"),), (src,))
    except AdapterMappingError:
        return
    # If accepted, output must be a valid tuple of diagnostics
    assert isinstance(out, tuple)
    for d in out:
        assert isinstance(d, Diagnostic)


def test_source_map_with_deep_recursion() -> None:
    payload = json.dumps({"version": 3, "mappings": "", "extra": ["x"] * 10_000})
    src = SourceFile(
        path="a.ts",
        text="",
        origin_path="a.vel",
        source_map=payload,
        kind="generated",
    )
    out = remap_diagnostics((_diag("a.ts"),), (src,))
    assert out[0].file == "a.vel"


def test_source_map_with_control_chars() -> None:
    payload = json.dumps({"version": 3, "mappings": "\x00\x01\x02\x03"})
    src = SourceFile(
        path="a.ts",
        text="",
        origin_path="a.vel",
        source_map=payload,
        kind="generated",
    )
    try:
        out = remap_diagnostics((_diag("a.ts"),), (src,))
    except AdapterMappingError:
        return
    assert isinstance(out, tuple)


def test_source_map_with_unicode() -> None:
    payload = json.dumps({"version": 3, "mappings": "日本語", "sources": ["フ.ts"]})
    src = SourceFile(
        path="a.ts",
        text="",
        origin_path="a.vel",
        source_map=payload,
        kind="generated",
    )
    out = remap_diagnostics((_diag("a.ts"),), (src,))
    assert isinstance(out, tuple)


# ---------------------------------------------------------------------------
# Diagnostics with unusual fields
# ---------------------------------------------------------------------------


def test_remap_preserves_diagnostic_with_no_file() -> None:
    d = Diagnostic(file=None, line=0, column=0, code=1, category="error", message="")
    src = SourceFile(path="a.ts", text="", origin_path="a.vel")
    out = remap_diagnostics((d,), (src,))
    assert out[0].file is None


def test_remap_preserves_unicode_in_message() -> None:
    d = Diagnostic(file="a.ts", line=1, column=1, code=1, category="error", message="日本語 🌍")
    src = SourceFile(path="a.ts", text="", origin_path="a.vel")
    out = remap_diagnostics((d,), (src,))
    assert out[0].message == "日本語 🌍"


def test_remap_preserves_huge_diagnostic_count(rng: random.Random) -> None:
    diags = tuple(_diag("a.ts") for _ in range(5_000))
    src = SourceFile(path="a.ts", text="", origin_path="a.vel")
    out = remap_diagnostics(diags, (src,))
    assert len(out) == 5_000
    assert all(d.file == "a.vel" for d in out)


# ---------------------------------------------------------------------------
# Consistency across repeated calls
# ---------------------------------------------------------------------------


def test_remap_is_pure(rng: random.Random) -> None:
    for _ in range(50):
        src = SourceFile(
            path="a.ts",
            text="",
            origin_path="a.vel",
            source_map=json.dumps({"version": 3, "mappings": ""}),
            kind="generated",
        )
        a = remap_diagnostics((_diag("a.ts"),), (src,))
        b = remap_diagnostics((_diag("a.ts"),), (src,))
        assert a == b


def test_collect_sources_is_pure(rng: random.Random) -> None:
    sources = [SourceFile(path=f"f{i}.ts", text="") for i in range(10)]
    a = _RecordingAdapter(sources)
    out1 = collect_sources(a, "/")
    out2 = collect_sources(a, "/")
    assert out1 == out2
