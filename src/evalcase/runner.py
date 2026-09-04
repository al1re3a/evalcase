from __future__ import annotations

import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence


@dataclass(frozen=True)
class CaseResult:
    name: str
    passed: bool
    duration_ms: int
    exit_code: int
    failures: tuple[str, ...]
    output: str
    stderr: str


@dataclass(frozen=True)
class SuiteResult:
    passed: int
    failed: int
    duration_ms: int
    cases: tuple[CaseResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "failed": self.failed, "duration_ms": self.duration_ms, "cases": [asdict(case) for case in self.cases]}


def load_suite(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = data.get("cases") if isinstance(data, dict) else data
    if not isinstance(cases, list) or not cases:
        raise ValueError("suite must contain a non-empty cases array")
    for index, case in enumerate(cases):
        if not isinstance(case, dict) or not case.get("name") or "input" not in case:
            raise ValueError(f"case {index} requires name and input")
        if not isinstance(case.get("assert", {}), dict):
            raise ValueError(f"case {index} assert must be an object")
    return cases


def _dig(value: Any, dotted_path: str) -> Any:
    current = value
    for part in dotted_path.split("."):
        if isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError(dotted_path)
    return current


def _items(value: Any) -> list[str]:
    if value is None:
        return []
    return [str(item) for item in value] if isinstance(value, list) else [str(value)]


def evaluate_output(output: str, exit_code: int, assertions: dict[str, Any]) -> tuple[str, ...]:
    failures: list[str] = []
    expected_exit = int(assertions.get("exit_code", 0))
    if exit_code != expected_exit:
        failures.append(f"exit_code: expected {expected_exit}, got {exit_code}")
    if "equals" in assertions and output.strip() != str(assertions["equals"]).strip():
        failures.append("equals: output did not match")
    for needle in _items(assertions.get("contains")):
        if needle not in output:
            failures.append(f"contains: missing {needle!r}")
    for needle in _items(assertions.get("not_contains")):
        if needle in output:
            failures.append(f"not_contains: found {needle!r}")
    for pattern in _items(assertions.get("regex")):
        if re.search(pattern, output, re.MULTILINE) is None:
            failures.append(f"regex: no match for {pattern!r}")
    json_assertions = assertions.get("json", {})
    if json_assertions:
        try:
            decoded = json.loads(output)
            for dotted_path, expected in json_assertions.items():
                try:
                    actual = _dig(decoded, dotted_path)
                    if actual != expected:
                        failures.append(f"json.{dotted_path}: expected {expected!r}, got {actual!r}")
                except KeyError:
                    failures.append(f"json.{dotted_path}: path not found")
        except json.JSONDecodeError:
            failures.append("json: output is not valid JSON")
    return tuple(failures)


def _run_case(case: dict[str, Any], command: Sequence[str], timeout: float) -> CaseResult:
    started = time.perf_counter()
    try:
        completed = subprocess.run(command, input=str(case["input"]), text=True, capture_output=True, timeout=timeout, shell=False, check=False)
        failures = evaluate_output(completed.stdout, completed.returncode, case.get("assert", {}))
        return CaseResult(str(case["name"]), not failures, int((time.perf_counter() - started) * 1000), completed.returncode, failures, completed.stdout, completed.stderr)
    except subprocess.TimeoutExpired as error:
        output = error.stdout if isinstance(error.stdout, str) else ""
        return CaseResult(str(case["name"]), False, int((time.perf_counter() - started) * 1000), 124, (f"timeout after {timeout}s",), output, "")


def run_suite(cases: list[dict[str, Any]], command: Sequence[str], jobs: int = 1, timeout: float = 30.0) -> SuiteResult:
    if not command:
        raise ValueError("command cannot be empty")
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        results = tuple(pool.map(lambda case: _run_case(case, command, timeout), cases))
    passed = sum(case.passed for case in results)
    return SuiteResult(passed, len(results) - passed, int((time.perf_counter() - started) * 1000), results)
