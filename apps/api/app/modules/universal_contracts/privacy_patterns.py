"""Padroes de deteccao de segredo, credencial, PII e dado financeiro.

Por que este modulo existe
--------------------------

Estes padroes nasceram no Learning Plane (`training_data/privacy.py`), onde
protegiam candidatos de treino. A Evidence Platform precisa exatamente da mesma
protecao na porta de entrada — e duas copias da mesma lista divergiriam na
primeira vez que alguem acrescentasse um padrao em um lado so.

O modulo vive no Shared Kernel porque a pergunta "isto e segredo?" nao pertence
a plano nenhum: e a mesma pergunta na ingestao e na promocao a candidato.

`training_data/privacy.py` continua sendo a API do Learning Plane e mapeia
estes padroes para o seu proprio `PrivacyFinding`. O comportamento nao mudou;
apenas deixou de existir em duas copias.

O que NAO fica aqui
-------------------

O valor detectado. Estas funcoes devolvem CODIGO, CATEGORIA e CAMINHO — nunca o
trecho que casou. Devolver o trecho colocaria o segredo no log, na resposta de
erro e no relatorio de auditoria, que sao exatamente os tres lugares onde ele
nao pode estar.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

# Chaves cujo simples NOME ja indica conteudo bruto de conversa. Nao se
# inspeciona o valor: o campo nao deveria existir.
RAW_CONTENT_KEYS: frozenset[str] = frozenset(
    {
        "conversation",
        "messages",
        "raw_conversation",
        "raw_prompt",
        "raw_response",
        "transcript",
    }
)

RAW_CONTENT_CODE = "RAW_CONVERSATION_FIELD_DETECTED"
RAW_CONTENT_CATEGORY = "raw_content"

# (codigo, categoria, padrao). A ordem nao importa: todos sao avaliados.
SENSITIVE_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
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

RAW_CONTENT_SENTINEL = "__RAW_CONTENT_KEY__"


def walk_strings(value: Any, path: str) -> Iterator[tuple[str, str]]:
    """Percorre o payload devolvendo `(caminho, texto)`.

    Emite `RAW_CONTENT_SENTINEL` quando o NOME da chave ja denuncia conteudo
    bruto — antes e independentemente do que ela contenha.
    """
    if isinstance(value, str):
        yield path, value
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_strings(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if str(key).strip().lower() in RAW_CONTENT_KEYS:
                yield child_path, RAW_CONTENT_SENTINEL
            yield from walk_strings(item, child_path)


def detect(value: Any, *, root: str = "payload") -> list[tuple[str, str, str]]:
    """Achados como `(codigo, categoria, caminho)`, ordenados e sem duplicatas.

    Nunca devolve o valor detectado — ver o docstring do modulo.
    """
    found: dict[tuple[str, str], tuple[str, str, str]] = {}
    for field_path, text in walk_strings(value, root):
        if text == RAW_CONTENT_SENTINEL:
            found[(RAW_CONTENT_CODE, field_path)] = (
                RAW_CONTENT_CODE,
                RAW_CONTENT_CATEGORY,
                field_path,
            )
            continue
        for code, category, pattern in SENSITIVE_PATTERNS:
            if pattern.search(text):
                found[(code, field_path)] = (code, category, field_path)
    return sorted(found.values(), key=lambda item: (item[2], item[0]))
