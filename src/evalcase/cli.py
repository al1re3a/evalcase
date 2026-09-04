from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from .runner import load_suite, run_suite


def junit(result, suite_name: str) -> str:
    cases = []
    for case in result.cases:
        failure = "" if case.passed else f"<failure message={quoteattr('; '.join(case.failures))}>{escape(case.output)}</failure>"
        cases.append(f"<testcase name={quoteattr(case.name)} time=\"{case.duration_ms / 1000:.3f}\">{failure}</testcase>")
    return f"<?xml version=\"1.0\" encoding=\"UTF-8\"?><testsuite name={quoteattr(suite_name)} tests=\"{len(result.cases)}\" failures=\"{result.failed}\" time=\"{result.duration_ms / 1000:.3f}\">{''.join(cases)}</testsuite>"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="evalcase", description="Deterministic regression tests for any agent CLI")
    parser.add_argument("suite")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--format", choices=("text", "json", "junit"), default="text")
    parser.add_argument("--output", help="Write report to a file")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command after --; case input is sent on stdin")
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("provide a command after --")
    cases = load_suite(args.suite)
    result = run_suite(cases, command, jobs=args.jobs, timeout=args.timeout)
    if args.format == "json":
        rendered = json.dumps(result.to_dict(), indent=2)
    elif args.format == "junit":
        rendered = junit(result, Path(args.suite).stem)
    else:
        lines = [f"EvalCase: {result.passed} passed, {result.failed} failed ({result.duration_ms}ms)"]
        for case in result.cases:
            lines.append(f"{'PASS' if case.passed else 'FAIL'} {case.name} ({case.duration_ms}ms)")
            lines.extend(f"  - {failure}" for failure in case.failures)
        rendered = "\n".join(lines)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
