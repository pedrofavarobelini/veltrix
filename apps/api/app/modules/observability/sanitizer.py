import re
from typing import Any


MAX_STRING_CHARS = 4_000
MAX_LIST_ITEMS = 50
MAX_DICT_ITEMS = 100

SENSITIVE_KEY_PARTS = {
    "api_key",
    "apikey",
    "authorization",
    "ciphertext",
    "client_secret",
    "cookie",
    "password",
    "private_key",
    "secret",
    "senha",
    "system_prompt",
    "token",
}

FINANCIAL_CONTEXT_KEYS = {
    "accounts",
    "bank_accounts",
    "debts",
    "financial_context",
    "financial_data",
    "finance_context",
    "transactions",
}

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|authorization|client[_-]?secret|cookie|password|secret|senha|token)"
    r"\b\s*[:=]\s*[^\s,;]+"
)
_BEARER = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{8,}=*")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_OPENAI_KEY = re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")
_GOOGLE_KEY = re.compile(r"\bAIza[0-9A-Za-z_-]{25,}\b")
_GITHUB_TOKEN = re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")
_SLACK_TOKEN = re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def sanitize_text(value: Any, max_chars: int = MAX_STRING_CHARS) -> str:
    text = str(value or "")
    text = _SECRET_ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
    text = _BEARER.sub("Bearer [REDACTED]", text)
    text = _JWT.sub("[REDACTED_JWT]", text)
    text = _OPENAI_KEY.sub("[REDACTED_KEY]", text)
    text = _GOOGLE_KEY.sub("[REDACTED_KEY]", text)
    text = _GITHUB_TOKEN.sub("[REDACTED_TOKEN]", text)
    text = _SLACK_TOKEN.sub("[REDACTED_TOKEN]", text)
    text = _EMAIL.sub("[REDACTED_EMAIL]", text)
    if len(text) > max_chars:
        return text[:max_chars] + "…[TRUNCATED]"
    return text


def _normalized_key(key: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")


def _is_sensitive_key(key: str) -> bool:
    return any(part in key for part in SENSITIVE_KEY_PARTS)


def _sanitize(value: Any, path: str, removed: list[str]) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for index, (raw_key, raw_value) in enumerate(value.items()):
            if index >= MAX_DICT_ITEMS:
                removed.append(f"{path}.*[limit]")
                break
            key = str(raw_key)
            normalized = _normalized_key(key)
            child_path = f"{path}.{key}" if path else key
            if _is_sensitive_key(normalized):
                removed.append(child_path)
                result[key] = "[REDACTED]"
                continue
            if normalized in FINANCIAL_CONTEXT_KEYS:
                removed.append(child_path)
                field_names = (
                    sorted(str(item) for item in raw_value.keys())[:25]
                    if isinstance(raw_value, dict)
                    else []
                )
                result[key] = {
                    "omitted": True,
                    "reason": "full_financial_context_not_stored",
                    "field_names": field_names,
                }
                continue
            result[key] = _sanitize(raw_value, child_path, removed)
        return result

    if isinstance(value, (list, tuple, set)):
        values = list(value)
        if len(values) > MAX_LIST_ITEMS:
            removed.append(f"{path}.*[limit]")
        return [
            _sanitize(item, f"{path}[{index}]", removed)
            for index, item in enumerate(values[:MAX_LIST_ITEMS])
        ]

    if isinstance(value, str):
        sanitized = sanitize_text(value)
        if sanitized != value:
            removed.append(path)
        return sanitized

    if value is None or isinstance(value, (bool, int, float)):
        return value

    return sanitize_text(value)


def sanitize_payload(payload: Any) -> tuple[dict[str, Any], list[str]]:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    if not isinstance(payload, dict):
        payload = {"value": payload}

    removed: list[str] = []
    sanitized = _sanitize(payload, "", removed)
    unique_removed = list(dict.fromkeys(item for item in removed if item))
    return sanitized, unique_removed
