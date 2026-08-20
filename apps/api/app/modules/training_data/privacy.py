from __future__ import annotations

import re
from collections.abc import Iterator

from pydantic import JsonValue

from app.modules.training_data.schemas import PrivacyFinding

_RAW_CONTENT_KEYS = {
    "conversation",
    "messages",
    "raw_conversation",
    "raw_prompt",
    "raw_response",
    "transcript",
}

_SENSITIVE_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "SECRET_ASSIGNMENT_DETECTED",
        "secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|token|secret|password|passwd|senha)"
            r"\s*[:=]\s*[^\s,;]{4,}"
        ),
    ),
    (
        "PRIVATE_KEY_DETECTED",
        "credential",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "PROVIDER_TOKEN_DETECTED",
        "credential",
        re.compile(r"\b(?:sk|ghp|github_pat)-?[A-Za-z0-9_\-]{12,}\b"),
    ),
    (
        "CREDENTIAL_URL_DETECTED",
        "credential",
        re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb|redis)://[^\s:/]+:[^\s@]+@"),
    ),
    (
        "ENV_REFERENCE_DETECTED",
        "secret",
        re.compile(r"(?i)(?:^|[\\/\s])\.env(?:\.[A-Za-z0-9_-]+)?(?:$|[\\/\s])"),
    ),
    (
        "EMAIL_PII_DETECTED",
        "pii",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "CPF_PII_DETECTED",
        "pii",
        re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)"),
    ),
    (
        "PHONE_PII_DETECTED",
        "pii",
        re.compile(r"(?<!\d)(?:\+?55\s*)?\(?\d{2}\)?[\s-]*9?\d{4}[\s-]*\d{4}(?!\d)"),
    ),
    (
        "PAYMENT_CARD_DETECTED",
        "financial",
        re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"),
    ),
    (
        "PERSONAL_FINANCIAL_DATA_DETECTED",
        "financial",
        re.compile(r"(?i)\b(?:ag[eê]ncia|conta banc[aá]ria|chave pix|saldo pessoal)\b\s*[:=]"),
    ),
    (
        "PERSONAL_PATH_DETECTED",
        "pii",
        re.compile(r"(?i)(?:[A-Z]:\\Users\\[^\\\s]+|/home/[^/\s]+|/Users/[^/\s]+)"),
    ),
)


def _walk(value: JsonValue, path: str) -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if key.strip().lower() in _RAW_CONTENT_KEYS:
                yield child_path, "__RAW_CONTENT_KEY__"
            yield from _walk(item, child_path)


def scan_payload(sections: dict[str, JsonValue]) -> list[PrivacyFinding]:
    findings: dict[tuple[str, str], PrivacyFinding] = {}
    for field_path, text in _walk(sections, "candidate"):
        if text == "__RAW_CONTENT_KEY__":
            finding = PrivacyFinding(
                code="RAW_CONVERSATION_FIELD_DETECTED",
                category="raw_content",
                field_path=field_path,
            )
            findings[(finding.code, finding.field_path)] = finding
            continue
        for code, category, pattern in _SENSITIVE_PATTERNS:
            if pattern.search(text):
                finding = PrivacyFinding(
                    code=code,
                    category=category,
                    field_path=field_path,
                )
                findings[(finding.code, finding.field_path)] = finding
    return sorted(findings.values(), key=lambda item: (item.field_path, item.code))
