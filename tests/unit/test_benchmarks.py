"""Regression checks for real benchmark module loading and baseline comparisons."""

import json
from pathlib import Path

import pytest
from benchmarks import run as benchmark
from benchmarks import startup


def test_throughput_module_loads_with_dataclasses():
    module = benchmark._load_module(Path(benchmark.BENCHMARKS / "throughput.py"))
    assert module.FixtureMeasurement("fixture").name == "fixture"


@pytest.mark.parametrize("current, expected", [(120.0, True), (80.0, False)])
def test_baseline_rates_have_correct_direction(tmp_path, current, expected):
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps({"benchmarks": [{"name": "throughput", "data": {"bytes_per_second": 100.0}}]})
    )
    result = benchmark.BenchmarkResult("throughput", True, 1.0, {"bytes_per_second": current})
    assert benchmark.compare_baseline([result], baseline, 0.1)[0] is expected


def test_invalid_benchmark_result_is_failure(tmp_path):
    path = tmp_path / "invalid_result.py"
    path.write_text('def run():\n    return {"fixture": {"error": "missing"}}\n')
    result = benchmark.run_one(benchmark.BenchmarkSpec("invalid", str(path), "invalid output"))
    assert not result.ok
    assert "missing" in result.error


def test_non_dictionary_benchmark_result_is_failure(tmp_path):
    path = tmp_path / "invalid_result.py"
    path.write_text("def run():\n    return None\n")
    result = benchmark.run_one(benchmark.BenchmarkSpec("invalid", str(path), "invalid output"))
    assert not result.ok


def test_failed_import_is_not_a_negative_timing(tmp_path, monkeypatch):
    (tmp_path / "pytscheck.py").write_text('raise RuntimeError("broken import")\n')
    monkeypatch.setenv("PYTHONPATH", str(tmp_path))
    with pytest.raises(RuntimeError, match="broken import"):
        startup._time_import()
