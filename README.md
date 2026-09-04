# EvalCase

**Regression-test any agent through the CLI it already has.**

EvalCase is a tiny, provider-neutral runner for deterministic AI and agent evaluations. It sends each case to a command on stdin and checks exact text, substrings, regexes, exit codes, and nested JSON fields.

```bash
evalcase examples/cases.json -- python examples/echo_agent.py
```

## Why

Agent frameworks change quickly; your behavioral contract should not. EvalCase uses a plain JSON suite and any executable adapter, so the same cases can test a local model, hosted provider, RAG pipeline, or traditional CLI.

## Assertions

```json
{
  "name": "structured answer",
  "input": "Return service status",
  "assert": {
    "exit_code": 0,
    "contains": ["healthy"],
    "not_contains": ["password"],
    "regex": ["latency_ms"],
    "json": {"status": "ok", "metrics.latency_ms": 42}
  }
}
```

## CI-ready reports

```bash
evalcase cases.json --jobs 4 --timeout 60 --format json -- my-agent --json
evalcase cases.json --format junit --output eval-results/junit.xml -- my-agent
```

Commands are executed directly with `shell=False`; user input is sent over stdin rather than interpolated into a shell command.

## Design

- Zero runtime dependencies
- Parallel cases with stable input ordering
- Useful timeout and assertion failures
- No provider SDK or API-key convention
- JSON and JUnit output for CI

## Development

```bash
python -m unittest discover -s tests -v
```

## License

MIT
