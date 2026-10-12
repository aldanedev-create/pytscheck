"""Real compiler regressions found during the publication audit."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from pytscheck import CompilerOptions, SourceFile, check, check_file, check_project
from pytscheck.adapters.errors import AdapterProtocolError
from pytscheck.adapters.sources import collect_sources
from pytscheck.client import Client
from pytscheck.exceptions import ConfigurationError
from pytscheck.runner import RunResult, run


class Adapter:
    name = "regression"

    def __init__(self, sources: list[SourceFile]) -> None:
        self.sources = sources

    def get_sources(self, project_root: str) -> list[SourceFile]:
        return self.sources


@pytest.mark.parametrize("alias", ["./bad.ts", "././bad.ts", "folder/../bad.ts"])
def test_adapter_collision_cannot_hide_error(tmp_path: Path, alias: str) -> None:
    adapter = Adapter(
        [
            SourceFile("bad.ts", 'export const x: number = "bad";'),
            SourceFile(alias, "export const x: number = 1;"),
        ]
    )
    with pytest.raises(AdapterProtocolError):
        check_project(tmp_path, adapter=adapter)


def test_virtual_imports_with_normalized_paths(tsgo_binary: Path, tmp_path: Path) -> None:
    adapter = Adapter(
        [
            SourceFile("./folder/value.ts", "export const value: number = 1;"),
            SourceFile("./main.ts", "import { value } from './folder/value'; export { value };"),
        ]
    )
    assert check_project(tmp_path, adapter=adapter).success


@pytest.mark.parametrize("text", [None, 42, "a\x00b", "\ud800", "x" * (8 * 1024 * 1024 + 1)])
def test_invalid_adapter_text_is_protocol_error(text: object) -> None:
    adapter = Adapter([SourceFile("input.ts", text)])  # type: ignore[arg-type]
    with pytest.raises(AdapterProtocolError):
        collect_sources(adapter, ".")


@pytest.mark.parametrize("path", [".", "NUL.ts", "input.ts.", "input.ts ", "a:b.ts"])
def test_nonportable_adapter_paths_are_rejected(path: str) -> None:
    with pytest.raises(AdapterProtocolError):
        collect_sources(Adapter([SourceFile(path, "")]), ".")


def test_adapter_directory_file_collision() -> None:
    with pytest.raises(AdapterProtocolError):
        collect_sources(Adapter([SourceFile("a.ts", ""), SourceFile("a.ts/b.ts", "")]), ".")


@pytest.mark.parametrize(
    "options",
    [
        {"strcit": True},
        {"target": 42},
        {"target": "\ud800"},
        {"types": "node"},
        {"lib": [42]},
        {"strict": "false"},
        {"extra": []},
        {"extra": {"--": True}},
    ],
)
def test_invalid_options_use_configuration_error(options: dict) -> None:
    with pytest.raises(ConfigurationError):
        check("export const x = 1;", options=options)


def test_file_check_ignores_incidental_tsconfig(tsgo_binary: Path, tmp_path: Path) -> None:
    (tmp_path / "tsconfig.json").write_text('{"compilerOptions":{"strict":true}}')
    path = tmp_path / "input.ts"
    path.write_text("export const x: number = 1;")
    assert check_file(path).success
    path.write_text('export const x: number = "bad";')
    assert [d.code for d in check_file(path).errors] == [2322]


def test_file_jsdoc_reports_type_error(tsgo_binary: Path, tmp_path: Path) -> None:
    path = tmp_path / "input.js"
    path.write_text('/** @type {number} */\nexport const x = "bad";')
    result = check_file(path, options=CompilerOptions(extra={"allowJs": True, "checkJs": True}))
    assert [d.code for d in result.errors] == [2322]


def test_string_jsdoc_reports_type_error(tsgo_binary: Path) -> None:
    result = check(
        '/** @type {number} */\nexport const x = "bad";',
        filename="input.js",
        options=CompilerOptions(extra={"allowJs": True, "checkJs": True}),
    )
    assert [d.code for d in result.errors] == [2322]


def test_client_runner_is_honored_and_restored(tsgo_binary: Path) -> None:
    calls: list[list[str]] = []

    def recorded(args: list[str], *, cwd: Path | None = None) -> RunResult:
        calls.append(args)
        return run(args, cwd=cwd)

    assert Client(runner=recorded).check("export const x = 1;").success
    assert len(calls) == 1
    assert check("export const x = 1;").success
    assert len(calls) == 1


def test_client_runners_are_thread_isolated(tsgo_binary: Path) -> None:
    def execute(marker: str) -> list[str]:
        calls: list[str] = []

        def recorded(args: list[str], *, cwd: Path | None = None) -> RunResult:
            calls.append(marker)
            return run(args, cwd=cwd)

        assert Client(runner=recorded).check("export const x = 1;").success
        return calls

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(execute, ["a", "b"])) == [["a"], ["b"]]


def test_low_level_virtual_check_cannot_write_outside_temp(tmp_path: Path) -> None:
    from pytscheck.checker import check_sources_virtual

    outside = tmp_path / "outside.ts"
    with pytest.raises(AdapterProtocolError):
        check_sources_virtual((SourceFile(str(outside), "export const x = 1;"),))
    assert not outside.exists()


def test_adapter_constructor_failure_is_discovery_error(tmp_path: Path, monkeypatch) -> None:
    from pytscheck.adapters.discovery import discover_adapters
    from pytscheck.exceptions import AdapterDiscoveryError

    (tmp_path / "broken_review_adapter.py").write_text(
        "class Adapter:\n    def __init__(self):\n        raise ValueError('broken constructor')\n"
    )
    metadata = tmp_path / "review_adapter-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text("Name: review-adapter\nVersion: 1.0\n")
    (metadata / "entry_points.txt").write_text(
        "[pytscheck.tests.constructorfailure]\nbroken = broken_review_adapter:Adapter\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(AdapterDiscoveryError) as exc:
        discover_adapters("pytscheck.tests.constructorfailure")
    assert isinstance(exc.value.__cause__, ValueError)


def test_malformed_map_is_rejected_even_for_valid_source(tmp_path: Path) -> None:
    from pytscheck.exceptions import AdapterMappingError

    with pytest.raises(AdapterMappingError):
        check_project(
            tmp_path,
            adapter=Adapter(
                [
                    SourceFile(
                        "a.ts", "export const x = 1;", origin_path="a.component", source_map="{"
                    )
                ]
            ),
        )


def test_windows_style_diagnostic_filename_is_remapped() -> None:
    from pytscheck import Diagnostic
    from pytscheck.adapters.source_maps import remap_diagnostics

    diagnostic = Diagnostic("folder\\a.ts", 1, 1, 2322, "error", "type mismatch")
    result = remap_diagnostics(
        (diagnostic,), (SourceFile("folder/a.ts", "", origin_path="a.component"),)
    )
    assert result[0].file == "a.component"
