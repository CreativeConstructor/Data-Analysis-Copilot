"""Bounded generate, validate, execute, and repair orchestration."""
from django.conf import settings

from .executor import ExecutionFailure, execute
from .gemini import GeminiFailure, generate_code
from .privacy import sanitize_text


def analyze(question, schema, dataset_path, *, columns=None, history="", on_attempt=None, dataset=None):
    """Run one analysis and up to the configured number of code repairs.

    `on_attempt` is called after each completed attempt so a caller with a
    persisted Turn can save the bounded history incrementally. The returned
    history is also suitable for a Turn JSON field.
    """
    retry_limit = min(3, max(0, int(settings.ANALYSIS_MAX_RETRIES)))
    if dataset is not None:
        from .rag import build_schema_context
        schema = build_schema_context(dataset, question)
    attempts = []
    previous_code = ""
    previous_error = ""

    for attempt_number in range(1, retry_limit + 2):
        try:
            code = generate_code(
                question,
                schema,
                history=history,
                previous_code=previous_code,
                previous_error=previous_error,
            )
        except GeminiFailure as exc:
            record = {
                "attempt": attempt_number,
                "code": previous_code,
                "status": "failed",
                "error": sanitize_text(exc)[:300],
            }
            attempts.append(record)
            if on_attempt:
                on_attempt(record.copy())
            return {"status": "failed", "result": None, "code": previous_code,
                    "attempts": attempts, "error": record["error"]}

        try:
            result = execute(code, dataset_path, columns=columns)
        except ExecutionFailure as exc:
            error = sanitize_text(exc)[:300]
            record = {"attempt": attempt_number, "code": code,
                      "status": "failed", "error": error}
            attempts.append(record)
            if on_attempt:
                on_attempt(record.copy())
            if not exc.retryable or attempt_number > retry_limit:
                return {"status": "failed", "result": None, "code": code,
                        "attempts": attempts, "error": error}
            previous_code, previous_error = code, error
            continue

        record = {"attempt": attempt_number, "code": code,
                  "status": "succeeded", "error": None}
        attempts.append(record)
        if on_attempt:
            on_attempt(record.copy())
        return {"status": "succeeded", "result": result, "code": code,
                "attempts": attempts, "error": None}

    # The loop always returns; this is defensive if its bounds change later.
    return {"status": "failed", "result": None, "code": previous_code,
            "attempts": attempts, "error": "Analysis could not be completed."}
