"""End-to-end test that a third-party adapter can be plugged into pytscheck.

Uses a real adapter class that mimics what a consuming tool (teloc-py) would
do: extract TypeScript from a non-TypeScript file format, hand it over, and
receive diagnostics mapped back to the original file. The compiler is the
real bundled tsgo.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pytscheck import check_project
from pytscheck.adapters.errors import AdapterExtractionError
from pytscheck.adapters.registry import register_adapter, unregister_adapter
from pytscheck.adapters.source_maps import remap_diagnostics
from pytscheck.adapters.sources import collect_sources
from pytscheck.checker import check_sources_virtual
from pytscheck.models import Result, SourceFile

# ---------------------------------------------------------------------------
# A minimal third-party adapter, mimicking teloc-py
# ---------------------------------------------------------------------------


_SCRIPT_RE = re.compile(r"<script[^>]*>(?P<body>.*?)</script>", re.DOTALL)


class _VelAdapter:
    """Adapter for a hypothetical `.vel` single-file-component format.

    Extracts the `<script>` block and treats it as TypeScript. Records
    the byte offset of the block so diagnostics can be attributed back
    to the original file.
    """

    @property
    def name(self) -> str:
        return "vel-test"

    def get_sources(self, project_root: str) -> list[SourceFile]:
        root = Path(project_root)
        if not root.is_dir():
            raise AdapterExtractionError(f"not a directory: {project_root}")

        sources: list[SourceFile] = []
        for vel in sorted(root.rglob("*.vel")):
            text = vel.read_text(encoding="utf-8")
            match = _SCRIPT_RE.search(text)
            if match is None:
                raise AdapterExtractionError(f"no <script> block found in {vel.name}")
            body = match.group("body")
            # Virtual path: unique per source. Preserve directory structure.
            rel = vel.relative_to(root)
            virtual = f"{rel}.ts"
            sources.append(
                SourceFile(
                    path=virtual,
                    text=body,
                    origin_path=str(rel),
                    kind="generated",
                )
            )
        return sources


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vel_project_clean(tmp_path: Path) -> Path:
    (tmp_path / "App.vel").write_text(
        "<template><div /></template>\n<script>\nexport const msg: string = 'hello';\n</script>\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def vel_project_error(tmp_path: Path) -> Path:
    (tmp_path / "App.vel").write_text(
        "<template><div /></template>\n"
        "<script>\n"
        "const age: number = 'twenty';\n"
        "export { age };\n"
        "</script>\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def vel_project_broken(tmp_path: Path) -> Path:
    (tmp_path / "Broken.vel").write_text(
        "<template><div /></template>\n<script>\nexport const x: number = 1;\n",  # unterminated
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def registered_vel_adapter():
    a = _VelAdapter()
    register_adapter(a)
    yield a
    unregister_adapter(a.name)


# ---------------------------------------------------------------------------
# Source collection
# ---------------------------------------------------------------------------


def test_adapter_collects_one_source_per_file(vel_project_clean: Path) -> None:
    sources = collect_sources(_VelAdapter(), str(vel_project_clean))
    assert len(sources) == 1
    assert sources[0].origin_path == "App.vel"
    assert sources[0].kind == "generated"


def test_adapter_collects_multiple_files(tmp_path: Path) -> None:
    for name in ("A.vel", "B.vel", "C.vel"):
        (tmp_path / name).write_text(
            "<script>export const x: number = 1;</script>",
            encoding="utf-8",
        )
    sources = collect_sources(_VelAdapter(), str(tmp_path))
    assert len(sources) == 3
    assert {s.origin_path for s in sources} == {"A.vel", "B.vel", "C.vel"}


def test_adapter_raises_extraction_error_on_missing_block(
    vel_project_broken: Path,
) -> None:
    with pytest.raises(AdapterExtractionError, match="no <script> block"):
        collect_sources(_VelAdapter(), str(vel_project_broken))


def test_adapter_raises_on_non_directory(tmp_path: Path) -> None:
    f = tmp_path / "file.vel"
    f.write_text("<script></script>")
    with pytest.raises(AdapterExtractionError, match="not a directory"):
        collect_sources(_VelAdapter(), str(f))


# ---------------------------------------------------------------------------
# End-to-end check
# ---------------------------------------------------------------------------


def test_clean_vel_project_passes(tsgo_binary: Path, vel_project_clean: Path) -> None:
    sources = collect_sources(_VelAdapter(), str(vel_project_clean))
    r = check_sources_virtual(sources)
    assert r.success


def test_vel_project_with_error_fails(tsgo_binary: Path, vel_project_error: Path) -> None:
    sources = collect_sources(_VelAdapter(), str(vel_project_error))
    r = check_sources_virtual(sources)
    assert not r.success
    assert any(d.code == 2322 for d in r.errors)


def test_diagnostics_remap_to_origin_file(tsgo_binary: Path, vel_project_error: Path) -> None:
    sources = collect_sources(_VelAdapter(), str(vel_project_error))
    r = check_sources_virtual(sources)
    remapped = remap_diagnostics(r.diagnostics, sources)
    errors = [d for d in remapped if d.category == "error"]
    assert errors
    assert any(d.file == "App.vel" for d in errors)


def test_remapped_error_keeps_origin_file_field(tsgo_binary: Path, vel_project_error: Path) -> None:
    sources = collect_sources(_VelAdapter(), str(vel_project_error))
    r = check_sources_virtual(sources)
    remapped = remap_diagnostics(r.diagnostics, sources)
    for d in remapped:
        if d.category == "error" and d.file == "App.vel":
            assert d.origin_file is not None
            assert d.origin_file.endswith(".vel.ts")


# ---------------------------------------------------------------------------
# The public API path
# ---------------------------------------------------------------------------


def test_check_project_with_adapter(tsgo_binary: Path, vel_project_clean: Path) -> None:
    r = check_project(vel_project_clean, adapter=_VelAdapter())
    assert isinstance(r, Result)
    assert r.success, [d.message for d in r.errors]


def test_check_project_with_adapter_reports_errors(
    tsgo_binary: Path, vel_project_error: Path
) -> None:
    r = check_project(vel_project_error, adapter=_VelAdapter())
    assert not r.success
    assert any(d.file == "App.vel" for d in r.errors)


def test_check_project_with_broken_adapter_raises(
    tsgo_binary: Path, vel_project_broken: Path
) -> None:
    with pytest.raises(AdapterExtractionError):
        check_project(vel_project_broken, adapter=_VelAdapter())


# ---------------------------------------------------------------------------
# Registered adapter path
# ---------------------------------------------------------------------------


def test_registered_adapter_is_discoverable(registered_vel_adapter) -> None:
    from pytscheck.adapters.registry import get_adapter

    assert get_adapter("vel-test") is registered_vel_adapter


def test_registered_adapter_used_via_instance(
    tsgo_binary: Path, vel_project_clean: Path, registered_vel_adapter
) -> None:
    r = check_project(vel_project_clean, adapter=registered_vel_adapter)
    assert r.success


# ---------------------------------------------------------------------------
# Isolation between runs
# ---------------------------------------------------------------------------


def test_adapter_does_not_write_into_project_dir(
    tsgo_binary: Path, vel_project_clean: Path
) -> None:
    before = set(vel_project_clean.iterdir())
    check_project(vel_project_clean, adapter=_VelAdapter())
    after = set(vel_project_clean.iterdir())
    assert before == after


def test_adapter_runs_multiple_times_consistently(
    tsgo_binary: Path, vel_project_error: Path
) -> None:
    r1 = check_project(vel_project_error, adapter=_VelAdapter())
    r2 = check_project(vel_project_error, adapter=_VelAdapter())
    assert r1.success == r2.success
    assert [d.code for d in r1.errors] == [d.code for d in r2.errors]
