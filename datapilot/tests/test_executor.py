from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess as system_subprocess
from django.test import SimpleTestCase, override_settings
from unittest.mock import patch
from datapilot.services.executor import ExecutionFailure, execute

class ExecutorTests(SimpleTestCase):
    def test_validated_code_runs_in_worker_and_returns_bounded_table(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "sales.csv"
            path.write_text("region,revenue\nNorth,100\nSouth,150\nNorth,200\n", encoding="utf-8")
            result = execute("result = df.groupby('region', as_index=False)['revenue'].sum()", path)
        self.assertEqual(result["kind"], "table")
        self.assertEqual(result["columns"], ["region", "revenue"])
        self.assertEqual(result["rows"], [["North", 300], ["South", 150]])

    @override_settings(ANALYSIS_TIMEOUT_SECONDS=1)
    def test_worker_timeout_is_reported_without_retry(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "sales.csv"
            path.write_text("amount\n1\n", encoding="utf-8")
            with self.assertRaises(ExecutionFailure) as raised:
                execute("result = 1\nwhile True:\n    pass", path)
        self.assertFalse(raised.exception.retryable)
        self.assertEqual(str(raised.exception), "Analysis timed out.")

    def test_worker_sanitizes_generated_exception_values(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "private.csv"
            path.write_text("note\nprivate-customer-value\n", encoding="utf-8")
            with self.assertRaises(ExecutionFailure) as raised:
                execute("result = df\nraise ValueError(df.iloc[0, 0])", path)
        self.assertNotIn("private-customer-value", str(raised.exception))
        self.assertIn("ValueError", str(raised.exception))

    def test_worker_captures_and_caps_generated_stdout(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "sales.csv"
            path.write_text("amount\n1\n", encoding="utf-8")
            result = execute("result = df\nprint('x' * 20000)", path)
        self.assertLessEqual(len(result["stdout"]), 10000)

    @patch.dict("os.environ", {"GEMINI_API_KEY": "private-key", "DATABASE_URL": "private-database-url"})
    def test_worker_environment_omits_application_credentials(self):
        original_run = system_subprocess.run
        observed = {}
        def inspect_environment(*args, **kwargs):
            observed.update(kwargs["env"])
            return original_run(*args, **kwargs)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "sales.csv"
            path.write_text("amount\n1\n", encoding="utf-8")
            with patch("datapilot.services.executor.subprocess.run", side_effect=inspect_environment):
                execute("result = df['amount'].sum()", path)
        self.assertNotIn("GEMINI_API_KEY", observed)
        self.assertNotIn("DATABASE_URL", observed)
