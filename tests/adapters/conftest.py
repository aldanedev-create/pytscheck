"""Fixtures for the adapter test suite."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from pytscheck.adapters.registry import registered_adapters, unregister_adapter


@pytest.fixture(autouse=True)
def _clean_adapter_registry() -> Iterator[None]:
    """Ensure each test starts and ends with an empty registry."""
    for name in list(registered_adapters()):
        unregister_adapter(name)
    yield
    for name in list(registered_adapters()):
        unregister_adapter(name)


@pytest.fixture
def vel_project(tmp_path: Path) -> Path:
    """A fake .vel-style project with two components."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "Button.vel").write_text(
        "<template><button>Click</button></template>\n"
        "<script lang=\"ts\">\n"
        "export const label: string = \"Click me\";\n"
        "export function onClick(): void { console.log(label); }\n"
        "</script>\n",
        encoding="utf-8",
    )
    (tmp_path / "components" / "Counter.vel").write_text(
        "<template><span>0</span></template>\n"
        "<script lang=\"ts\">\n"
        "export const count: number = 0;\n"
        "</script>\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def vel_project_with_error(tmp_path: Path) -> Path:
    """A fake .vel project whose component has a type error."""
    (tmp_path / "App.vel").write_text(
        "<template><div /></template>\n"
        "<script lang=\"ts\">\n"
        "const age: number = \"twenty\";\n"
        "export { age };\n"
        "</script>\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def vel_project_broken(tmp_path: Path) -> Path:
    """A .vel file with an unterminated script block."""
    (tmp_path / "Broken.vel").write_text(
        "<template><div /></template>\n"
        "<script lang=\"ts\">\n"
        "export const x: number = 1;\n",  # missing </script>
        encoding="utf-8",
    )
    return tmp_path