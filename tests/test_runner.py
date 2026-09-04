import json
import sys
import tempfile
import unittest
from pathlib import Path

from evalcase.runner import evaluate_output, load_suite, run_suite


class RunnerTests(unittest.TestCase):
    def test_all_assertion_types(self):
        output = json.dumps({"answer": {"value": 42}, "note": "safe result"})
        failures = evaluate_output(output, 0, {"contains": "safe", "not_contains": "secret", "regex": r'"value":\s*42', "json": {"answer.value": 42}})
        self.assertEqual(failures, ())

    def test_failure_messages_are_specific(self):
        failures = evaluate_output("hello", 2, {"exit_code": 0, "contains": "world"})
        self.assertEqual(len(failures), 2)
        self.assertIn("expected 0", failures[0])

    def test_runs_command_without_shell(self):
        command = [sys.executable, "-c", "import sys; print(sys.stdin.read().upper())"]
        result = run_suite([{"name": "upper", "input": "hello", "assert": {"contains": "HELLO"}}], command)
        self.assertEqual(result.passed, 1)
        self.assertEqual(result.failed, 0)

    def test_load_suite_validates_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "suite.json")
            path.write_text('{"cases": []}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-empty"):
                load_suite(path)


if __name__ == "__main__":
    unittest.main()
