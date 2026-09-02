"""Servico da trilha unificada: registrar fatos e recuperar a operacao inteira.

Isolamento de projeto
---------------------

A chave e composta (`project_id`, `correlation_id`). Consultar a trilha de
outro projeto nao devolve lista vazia por filtro aplicado depois — a chave
simplesmente nao existe naquele namespace. Filtro pos-busca e uma peneira que
alguem um dia esquece de aplicar.

Redacao na entrada
------------------

Diferente da exportacao do Risk Console, aqui a redacao acontece na ENTRADA:
a trilha e um armazenamento de longa duracao, e um segredo que entra e um
segredo que fica. O que nao pode ser guardado nao e guardado.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone

from app.modules.correlation.schemas import (
    AuditEvent,
    AuditOutcome,
    AuditStage,
    AuditTrail,
)

# Chaves de referencia cujo VALOR nunca deve ser guardado, ainda que alguem as
# envie. A lista e de nomes, e nao de conteudo, porque adivinhar conteudo e
# uma corrida que a trilha perde.
_FORBIDDEN_REFERENCE_KEYS = frozenset(
    {
        "prompt",
        "request_text",
        "payload",
        "body",
        "api_key",
        "apikey",
        "token",
        "secret",
        "password",
        "senha",
        "authorization",
        "credential",
        "connection_string",
        "database_url",
    }
)

_SECRET_SHAPE = re.compile(
    r"(?i)(api[_-]?key|secret|password|token|bearer)\s*[:=]|"
    r"[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s/@]+@"
)


class CorrelationError(ValueError):
    """Recusa explicita na fronteira da trilha."""


def new_correlation_id(prefix: str = "corr") -> str:
    """Identificador novo para uma operacao que comeca aqui."""
    return f"{prefix}-{uuid.uuid4().hex[:24]}"


def derive_correlation_id(*parts: str) -> str:
    """Correlacao derivada de identificadores ja existentes.

    Util quando a operacao nasce de algo que ja tem identidade: repetir o
    mesmo par de partes devolve a mesma correlacao, e a trilha nao se
    fragmenta em duas por causa de um retry.
    """
    payload = "|".join(part.strip().lower() for part in parts if part)
    return "corr-" + hashlib.sha256(payload.encode()).hexdigest()[:24]


class AuditTrailService:
    """Trilha em memoria, com a mesma forma de um repositorio durável.

    Em memoria porque a trilha atravessa TODAS as camadas e precisa custar
    quase nada por evento. Quem precisar de durabilidade usa o Evidence
    Platform e o outbox, que ja existem e ja sao duráveis — e a trilha guarda
    a referencia para la.
    """

    def __init__(self, max_events_per_trail: int = 200) -> None:
        self._trails: dict[tuple[str, str], list[AuditEvent]] = {}
        self._max = max_events_per_trail

    def record(
        self,
        *,
        correlation_id: str,
        stage: AuditStage,
        action: str,
        outcome: AuditOutcome,
        project_id: str,
        producer: str,
        environment: str,
        policy_id: str | None = None,
        policy_version: str | None = None,
        reason_codes: tuple[str, ...] = (),
        references: dict[str, str] | None = None,
        now: datetime | None = None,
    ) -> AuditEvent:
        """Registra um fato. Recusa qualquer coisa que pareca conteudo."""
        limpas = self._sanitize(references or {})
        project = project_id.strip().lower()

        evento = AuditEvent(
            event_id=f"audit_{uuid.uuid4().hex[:20]}",
            correlation_id=correlation_id,
            stage=stage,
            action=action,
            outcome=outcome,
            project_id=project,
            producer=producer,
            environment=environment,
            occurred_at=now or datetime.now(timezone.utc),
            policy_id=policy_id,
            policy_version=policy_version,
            reason_codes=tuple(reason_codes),
            references=limpas,
        )

        chave = (project, correlation_id)
        eventos = self._trails.setdefault(chave, [])
        if len(eventos) >= self._max:
            # Trilha ilimitada vira vazamento de memoria com aparencia de
            # recurso. O limite e explicito e a recusa e visivel.
            raise CorrelationError(
                f"Trilha {correlation_id} excedeu {self._max} eventos; "
                "a operação provavelmente está em laço."
            )
        eventos.append(evento)
        return evento

    def trail(self, project_id: str, correlation_id: str) -> AuditTrail:
        """A operacao inteira, na ordem em que aconteceu."""
        project = project_id.strip().lower()
        eventos = list(self._trails.get((project, correlation_id), []))
        return AuditTrail(
            correlation_id=correlation_id, project_id=project, events=eventos
        )

    def correlations(self, project_id: str, limit: int = 50) -> list[str]:
        project = project_id.strip().lower()
        encontradas = [
            correlacao
            for (dono, correlacao) in self._trails
            if dono == project
        ]
        return sorted(encontradas)[:limit]

    def reset(self) -> None:
        self._trails.clear()

    @staticmethod
    def _sanitize(references: dict[str, str]) -> dict[str, str]:
        """Recusa a chave proibida e o valor com cara de segredo.

        Recusar, e nao redigir em silencio: quem tentou gravar um segredo
        precisa saber que tentou. Redigir sem avisar treinaria o chamador a
        continuar mandando.
        """
        limpas: dict[str, str] = {}
        for chave, valor in references.items():
            normal = chave.strip().lower()
            if normal in _FORBIDDEN_REFERENCE_KEYS:
                raise CorrelationError(
                    f"Referência '{chave}' não pode entrar na trilha: "
                    "a trilha guarda ponteiro, nunca conteúdo nem segredo."
                )
            if _SECRET_SHAPE.search(str(valor)):
                raise CorrelationError(
                    f"Referência '{chave}' tem forma de segredo e foi recusada."
                )
            limpas[normal] = str(valor)
        return limpas


audit_trail_service = AuditTrailService()
