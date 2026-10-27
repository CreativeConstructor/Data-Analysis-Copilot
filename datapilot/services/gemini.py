import os
import re
from django.conf import settings
from .prompt_template import build_prompt

class GeminiFailure(Exception):
    def __init__(self, message, retryable=False):
        self.retryable = retryable
        super().__init__(message)

def generate_code(question, schema, history="", previous_code="", previous_error=""):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiFailure("Gemini API key is not configured.")
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=settings.GEMINI_REQUEST_TIMEOUT_SECONDS * 1000))
        response = client.models.generate_content(model=settings.GEMINI_MODEL,
            contents=build_prompt(question, schema, history, previous_code, previous_error))
        code = (response.text or "").strip()
        code = re.sub(r"^```(?:python)?\s*|\s*```$", "", code, flags=re.IGNORECASE).strip()
        if not code:
            raise GeminiFailure("Gemini returned an empty code response.", retryable=True)
        return code
    except GeminiFailure:
        raise
    except Exception as exc:
        name = type(exc).__name__
        status = getattr(exc, "status_code", getattr(exc, "code", None))
        if status == 429 or "rate" in name.lower() or "quota" in name.lower():
            raise GeminiFailure("Gemini rate limit reached.") from None
        if "timeout" in name.lower():
            raise GeminiFailure("Gemini request timed out.") from None
        raise GeminiFailure(f"Gemini request failed ({name}).") from None
