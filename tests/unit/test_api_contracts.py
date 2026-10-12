"""Unit tests for the public API contract.

This file asserts the shape of the API, not its behavior. Behavior is
covered elsewhere. Here we lock the contract that downstream code depends
on: parameter names, kinds, defaults, and return annotations.
"""

from __future__ import annotations

import inspect

import pytest

import pytscheck
from pytscheck import check, check_file, check_project

# --- check() ----------------------------------------------------------------


def test_check_is_callable() -> None:
    assert callable(check)


def test_check_parameters_exact() -> None:
    sig = inspect.signature(check)
    assert list(sig.parameters) == ["source", "filename", "options", "keep_raw"]


def test_check_source_is_positional_or_keyword() -> None:
    sig = inspect.signature(check)
    p = sig.parameters["source"]
    assert p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_check_other_params_are_keyword_only() -> None:
    sig = inspect.signature(check)
    for name in ("filename", "options", "keep_raw"):
        p = sig.parameters[name]
        assert p.kind is inspect.Parameter.KEYWORD_ONLY, name


def test_check_defaults() -> None:
    sig = inspect.signature(check)
    assert sig.parameters["filename"].default == "input.ts"
    assert sig.parameters["options"].default is None
    assert sig.parameters["keep_raw"].default is False


def test_check_return_annotation() -> None:
    sig = inspect.signature(check)
    assert sig.return_annotation is not inspect.Parameter.empty


# --- check_file() -----------------------------------------------------------


def test_check_file_parameters_exact() -> None:
    sig = inspect.signature(check_file)
    assert list(sig.parameters) == ["path", "options", "keep_raw"]


def test_check_file_path_is_positional_or_keyword() -> None:
    sig = inspect.signature(check_file)
    p = sig.parameters["path"]
    assert p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_check_file_optional_params_are_keyword_only() -> None:
    sig = inspect.signature(check_file)
    for name in ("options", "keep_raw"):
        assert sig.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY


def test_check_file_return_annotation() -> None:
    sig = inspect.signature(check_file)
    assert sig.return_annotation is not inspect.Parameter.empty


# --- check_project() --------------------------------------------------------


def test_check_project_parameters_exact() -> None:
    sig = inspect.signature(check_project)
    assert list(sig.parameters) == ["project_root", "options", "adapter", "keep_raw"]


def test_check_project_root_is_positional_or_keyword() -> None:
    sig = inspect.signature(check_project)
    p = sig.parameters["project_root"]
    assert p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_check_project_optional_params_are_keyword_only() -> None:
    sig = inspect.signature(check_project)
    for name in ("options", "adapter", "keep_raw"):
        assert sig.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY


def test_check_project_adapter_default_is_none() -> None:
    sig = inspect.signature(check_project)
    assert sig.parameters["adapter"].default is None


def test_check_project_return_annotation() -> None:
    sig = inspect.signature(check_project)
    assert sig.return_annotation is not inspect.Parameter.empty


# --- __all__ ----------------------------------------------------------------


def test_all_names_exist() -> None:
    for name in pytscheck.__all__:
        assert hasattr(pytscheck, name), f"missing: {name}"


def test_all_has_no_duplicates() -> None:
    assert len(pytscheck.__all__) == len(set(pytscheck.__all__))


def test_all_is_tuple_or_list() -> None:
    assert isinstance(pytscheck.__all__, (list, tuple))


def test_all_entries_are_nonempty_strings() -> None:
    for name in pytscheck.__all__:
        assert isinstance(name, str)
        assert name


def test_version_names_precede_api_names() -> None:
    i_version = pytscheck.__all__.index("__version__")
    i_check = pytscheck.__all__.index("check")
    assert i_version < i_check


# --- docstrings -------------------------------------------------------------


@pytest.mark.parametrize("fn", [check, check_file, check_project])
def test_public_functions_have_docstrings(fn) -> None:
    doc = inspect.getdoc(fn)
    assert doc and len(doc) > 20


@pytest.mark.parametrize("fn", [check, check_file, check_project])
def test_public_functions_document_raises(fn) -> None:
    doc = inspect.getdoc(fn) or ""
    assert "Raises:" in doc or "raise" in doc.lower()


@pytest.mark.parametrize("fn", [check, check_file, check_project])
def test_public_functions_document_returns(fn) -> None:
    doc = inspect.getdoc(fn) or ""
    assert "Returns:" in doc


# --- imports ----------------------------------------------------------------


def test_importing_api_does_not_import_runner_at_module_level() -> None:
    """Import in a fresh interpreter without executing a compiler subprocess."""
    import subprocess
    import sys

    code = (
        "import sys\n"
        "def audit(event, args):\n"
        "    if event == 'subprocess.Popen':\n"
        "        raise AssertionError('subprocess started during import')\n"
        "sys.addaudithook(audit)\n"
        "import pytscheck.api\n"
        "print('isolated import OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        shell=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "isolated import OK"


def test_project_adapter_annotation_keeps_exact_public_spelling() -> None:
    assert (
        inspect.signature(check_project).parameters["adapter"].annotation
        == "'CompilerAdapter | None'"
    )
