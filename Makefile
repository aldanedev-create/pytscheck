.PHONY: help install dev test lint type format coverage build clean binaries verify

help:
	@echo "Targets:"
	@echo "  install     Install package (runtime only)"
	@echo "  dev         Install with dev extras"
	@echo "  test        Run pytest"
	@echo "  lint        Run ruff check"
	@echo "  type        Run mypy"
	@echo "  format      Run ruff format"
	@echo "  coverage    Run pytest with coverage"
	@echo "  build       Build sdist + wheel"
	@echo "  binaries    Fetch bundled tsgo binaries (Phase 0)"
	@echo "  verify      Verify bundled binaries against manifest"
	@echo "  clean       Remove build artifacts"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check src tests scripts

type:
	mypy src/pytscheck

format:
	ruff format src tests scripts

coverage:
	pytest --cov=pytscheck --cov-report=term-missing

build:
	python -m build

binaries:
	python scripts/build_binaries.py $(PLATFORM)

verify:
	python scripts/verify_binaries.py

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +