"""Nox sessions for pytscheck."""
from __future__ import annotations

import nox

PYTHONS = ["3.11", "3.12", "3.13"]


@nox.session(python=PYTHONS)
def tests(session: nox.Session) -> None:
    """Run the test suite."""
    session.install("-e", ".[test]")
    session.run("pytest", *session.posargs)


@nox.session
def lint(session: nox.Session) -> None:
    session.install("-e", ".[dev]")
    session.run("ruff", "check", "src", "tests", "scripts")
    session.run("ruff", "format", "--check", "src", "tests", "scripts")


@nox.session
def typecheck(session: nox.Session) -> None:
    session.install("-e", ".[dev]")
    session.run("mypy", "src/pytscheck")


@nox.session
def coverage(session: nox.Session) -> None:
    session.install("-e", ".[test]")
    session.run("pytest", "--cov=pytscheck", "--cov-report=term-missing")


@nox.session
def build(session: nox.Session) -> None:
    session.install("build")
    session.run("python", "-m", "build")