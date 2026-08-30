"""Fronteira de autoridade: o que o consumidor declara x o que o PedroCore decide.

Por que este modulo existe
--------------------------

Um consumidor pode dizer o que observou. Ele nao pode dizer o que isso VALE.

A diferenca nao e filosofica, e operacional: se um payload puder trazer
`eligibility: eligible` ou `authorized: true`, entao qualquer integrador com
credencial vira dono da governanca de aprendizado do PedroCore. O Learning
Plane inteiro — privacidade, proveniencia, autorizacao, ciclo de vida — passa a
valer o que vale a boa-fe do cliente mais fraco.

Por isso a defesa nao e "ignorar o campo". Campo ignorado em silencio ensina o
integrador que ele funciona, e a proxima versao dele passa a depender disso.
A defesa e **recusar a requisicao inteira** e dizer qual campo causou a recusa.

O que e reservado
-----------------

Nomes que representam JULGAMENTO do servidor, nunca fato do produtor:

  - elegibilidade, autorizacao e classificacao final de privacidade;
  - identidade e status de Training Candidate;
  - prontidao e pertinencia a dataset;
  - score de qualidade autoritativo;
  - o proprio interruptor de coleta automatica.

Fato do produtor tem outro vocabulario e e bem-vindo: `observed_*`,
`reported_*`, `producer_asserted_*`. O contrato aceita a observacao e recusa a
sentenca.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Campos que so o PedroCore pode produzir. A comparacao e por nome normalizado
# (minusculas, sem `_`/`-`) porque `trainingCandidate`, `training_candidate` e
# `training-candidate` sao a mesma tentativa.
_RESERVED_FIELD_NAMES: frozenset[str] = frozenset(
    {
        # Julgamento do Learning Plane
        "eligibility",
        "eligible",
        "eligibilitydecision",
        "iseligible",
        "authorization",
        "authorized",
        "dataauthorization",
        "datauseauthorization",
        "allowsneuraltraining",
        "trainingauthorization",
        "privacyclassification",
        # Objetos internos que o consumidor nunca monta
        "trainingcandidate",
        "trainingexamplecandidate",
        "trainingcandidaterecord",
        "candidateid",
        "candidatelifecycle",
        "lifecycle",
        # Prontidao e dataset
        "datasetreadiness",
        "readiness",
        "datasetmembership",
        "canonicaldataset",
        "datasetid",
        # Julgamento de qualidade autoritativo
        "qualityscore",
        "authoritativequalityscore",
        "trustscore",
        "confidencescore",
        # O interruptor que nao existe
        "automaticcollection",
        "automaticcollectionperformed",
        "autocollect",
    }
)

# Prefixos que marcam explicitamente uma afirmacao do produtor. Um campo com
# esse prefixo nunca colide com a reserva, mesmo carregando a mesma palavra:
# `producer_asserted_eligibility` e uma alegacao, `eligibility` e uma sentenca.
_PRODUCER_ASSERTION_PREFIXES: tuple[str, ...] = (
    "observed",
    "reported",
    "producerasserted",
    "producerdeclared",
    "selfreported",
)

MAX_INSPECTION_DEPTH = 12


def _normalize(name: str) -> str:
    return name.replace("_", "").replace("-", "").strip().lower()


def _is_producer_assertion(normalized: str) -> bool:
    return normalized.startswith(_PRODUCER_ASSERTION_PREFIXES)


class AuthorityViolation(BaseModel):
    """Uma tentativa concreta de o consumidor decidir no lugar do servidor."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., min_length=1, max_length=512)
    field: str = Field(..., min_length=1, max_length=128)
    reason: str = Field(..., min_length=1, max_length=256)


def scan_for_reserved_authority(
    payload: Any,
    *,
    path: str = "$",
    depth: int = 0,
) -> list[AuthorityViolation]:
    """Procura campos reservados em qualquer profundidade do payload.

    A varredura e recursiva de proposito: esconder `eligibility` dentro de
    `metadata.extra.nested` nao pode ser mais eficaz do que envia-lo no topo.

    Nao inspeciona VALORES, apenas nomes de campo. O conteudo pode ser dado
    sensivel do produtor, e este modulo nao existe para ler dado — existe para
    reconhecer autoridade indevida.
    """
    if depth > MAX_INSPECTION_DEPTH:
        return []

    violations: list[AuthorityViolation] = []

    if isinstance(payload, BaseModel):
        return scan_for_reserved_authority(
            payload.model_dump(mode="json"), path=path, depth=depth
        )

    if isinstance(payload, dict):
        for raw_key, value in payload.items():
            key = str(raw_key)
            normalized = _normalize(key)
            child_path = f"{path}.{key}"
            if normalized in _RESERVED_FIELD_NAMES and not _is_producer_assertion(normalized):
                violations.append(
                    AuthorityViolation(
                        path=child_path,
                        field=key,
                        reason=(
                            "campo reservado ao PedroCore; o consumidor pode "
                            "relatar fato observado, nao emitir julgamento"
                        ),
                    )
                )
            violations.extend(
                scan_for_reserved_authority(value, path=child_path, depth=depth + 1)
            )
        return violations

    if isinstance(payload, (list, tuple)):
        for index, item in enumerate(payload):
            violations.extend(
                scan_for_reserved_authority(item, path=f"{path}[{index}]", depth=depth + 1)
            )
        return violations

    return violations


def reserved_field_names() -> frozenset[str]:
    """Nomes reservados, normalizados. Exposto para teste e documentacao."""
    return _RESERVED_FIELD_NAMES
