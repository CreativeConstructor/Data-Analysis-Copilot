import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from django.conf import settings
from .validator import validate

class ExecutionFailure(Exception):
    def __init__(self, message, retryable=False):
        self.retryable = retryable
        super().__init__(message)

def execute(code, dataset_path, columns=None):
    errors = validate(code, columns=columns)
    if errors:
        raise ExecutionFailure("; ".join(e["message"] for e in errors), retryable=True)
    worker = Path(__file__).with_name("worker.py")
    with tempfile.TemporaryDirectory(prefix="datapilot-") as workdir:
        env = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP") if key in os.environ}
        try:
            request = {"code": code, "dataset_path": str(dataset_path), "max_rows": settings.DATASET_MAX_ROWS,
                "max_result_rows": settings.ANALYSIS_MAX_RESULT_ROWS, "max_result_columns": settings.ANALYSIS_MAX_RESULT_COLUMNS,
                "max_output_bytes": settings.ANALYSIS_MAX_OUTPUT_BYTES}
            process = subprocess.run([sys.executable, "-I", str(worker)], input=json.dumps(request),
                capture_output=True, text=True, encoding="utf-8", timeout=settings.ANALYSIS_TIMEOUT_SECONDS, cwd=workdir, env=env)
        except subprocess.TimeoutExpired:
            raise ExecutionFailure("Analysis timed out.", retryable=False)
        if process.returncode != 0 or len(process.stdout.encode("utf-8")) > settings.ANALYSIS_MAX_OUTPUT_BYTES:
            raise ExecutionFailure("Analysis worker failed.", retryable=False)
        try:
            response = json.loads(process.stdout)
        except (json.JSONDecodeError, TypeError):
            raise ExecutionFailure("Analysis worker returned an invalid response.", retryable=False)
        if not response.get("ok"):
            error = response.get("error") or {}
            message = f"{error.get('type', 'AnalysisError')}: {error.get('message', 'Analysis failed.')[:200]}"
            message = re.sub(r"[A-Za-z]:\\[^\s'\"]+|/[^\s'\"]+", "[path]", message)
            raise ExecutionFailure(message, retryable=True)
        return response["result"]
