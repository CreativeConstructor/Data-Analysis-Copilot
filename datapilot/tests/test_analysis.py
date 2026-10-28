from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from datapilot.services.executor import ExecutionFailure
from datapilot.services.gemini import GeminiFailure
from datapilot.services.analysis import analyze


class AnalysisOrchestrationTests(SimpleTestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.dataset = Path(self.folder.name) / "sales.csv"
        self.dataset.write_text("sales\n10\n", encoding="utf-8")

    def tearDown(self):
        self.folder.cleanup()

    @patch("datapilot.services.analysis.execute")
    @patch("datapilot.services.analysis.generate_code")
    def test_runtime_error_is_sent_back_and_repaired(self, generate, execute):
        generate.side_effect = ["result = df['missing'].sum()", "result = df['sales'].sum()"]
        execute.side_effect = [ExecutionFailure("KeyError: missing column", retryable=True), {"kind": "scalar", "value": 10}]
        persisted = []

        result = analyze("sum sales", "sales: numeric", self.dataset,
                         columns=["sales"], on_attempt=persisted.append)

        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(len(result["attempts"]), 2)
        self.assertEqual(result["attempts"][0]["status"], "failed")
        self.assertEqual(len(persisted), 2)
        self.assertEqual(generate.call_args.kwargs["previous_code"], "result = df['missing'].sum()")
        self.assertIn("missing column", generate.call_args.kwargs["previous_error"])

    @override_settings(ANALYSIS_MAX_RETRIES=10)
    @patch("datapilot.services.analysis.execute", side_effect=ExecutionFailure("bad code", retryable=True))
    @patch("datapilot.services.analysis.generate_code", return_value="result = 1")
    def test_retry_limit_is_hard_capped_at_three(self, generate, execute):
        result = analyze("question", "schema", self.dataset)
        self.assertEqual(len(result["attempts"]), 4)
        self.assertEqual(generate.call_count, 4)

    @patch("datapilot.services.analysis.execute", side_effect=ExecutionFailure("worker stopped", retryable=False))
    @patch("datapilot.services.analysis.generate_code", return_value="result = 1")
    def test_non_retryable_execution_failure_stops_immediately(self, generate, execute):
        result = analyze("question", "schema", self.dataset)
        self.assertEqual(len(result["attempts"]), 1)
        self.assertEqual(generate.call_count, 1)

    @patch("datapilot.services.analysis.generate_code", side_effect=GeminiFailure("API unavailable"))
    def test_missing_or_unavailable_gemini_is_not_retried(self, generate):
        result = analyze("question", "schema", self.dataset)
        self.assertEqual(len(result["attempts"]), 1)
        self.assertEqual(result["status"], "failed")
