# Performance

Every check launches the native compiler. Small repeated checks include process-start overhead; checking a project groups its input graph into one invocation. PyTSCheck does not cache results or keep an incremental compiler alive.

## Measure the actual implementation

```bash
python benchmarks/run.py --list
python benchmarks/run.py --json > benchmarks.json
python benchmarks/run.py --json --save-baseline baseline.json
python benchmarks/run.py --baseline baseline.json --tolerance 0.10
```

`--json` emits machine-readable results on stdout and human progress on stderr. Benchmarks use real files/processes/diagnostics. A baseline comparison is meaningful on comparable hardware and environment; absolute hosted-CI timings are not a product latency promise.

The four benchmark families measure startup latency, diagnostic throughput, concurrent checks, and memory behavior. Read [benchmarks/README.md](../benchmarks/README.md) for commands and interpretation.

## Practical choices

Prefer project checks for sources sharing imports. Bound application-level concurrency because every worker creates a compiler process. Retain raw output only when needed. Test realistic dependency graphs rather than extrapolating from an isolated tiny source.

Python memory measurements do not represent the compiler child process's complete resident memory. Output limits and source-size checks are safety bounds, not a total memory budget. See [security](security.md).
