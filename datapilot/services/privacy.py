import re

SENSITIVE_COLUMN_WORDS = ("email", "phone", "mobile", "address", "ssn", "social security", "birth", "dob", "name", "username", "user id", "customer id", "person", "password", "token", "secret", "credential", "account number", "card number")
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)(?!\w)")
LONG_ID = re.compile(r"\b(?:\d{8,}|[A-F0-9]{16,})\b", re.I)

def sanitize_text(value):
    text = str(value)
    text = EMAIL.sub("[redacted-email]", text)
    text = PHONE.sub(lambda match: "[redacted-phone]" if sum(char.isdigit() for char in match.group()) >= 10 else match.group(), text)
    text = LONG_ID.sub("[redacted-id]", text)
    return text[:500]

def privacy_filtered_profile(profile):
    safe = []
    for item in profile.get("profile", []):
        name = sanitize_text(item.get("name", ""))
        sensitive = any(word in name.lower() for word in SENSITIVE_COLUMN_WORDS)
        safe.append({"name": name, "type": sanitize_text(item.get("type", "")),
            "missing_count": item.get("missing_count", 0), "distinct_count": item.get("distinct_count", 0),
            "statistics": item.get("statistics", {}),
            "samples": [] if sensitive else [sanitize_text(sample) for sample in item.get("samples", [])[:5]]})
    return {"rows": profile.get("rows"), "columns": profile.get("columns"), "profile": safe}
