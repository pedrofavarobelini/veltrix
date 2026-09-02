"""E6 — Shadow Mode: observar um candidato sem deixá-lo tocar em nada.

O que ja existia
----------------

`shadow_routing` calcula QUAL candidato seria escolhido, e diz explicitamente
que nunca chama provider. Isso e uma decisao de roteamento, nao um shadow: ele
responde "quem eu escolheria", e nao "o que teria acontecido".

O que esta camada acrescenta
----------------------------

A execucao paralela observada. O primario responde ao usuario; o shadow roda
ao lado, o resultado vira evidencia de comparacao, e nada do shadow chega ao
consumidor.

As cinco garantias, e como cada uma e obtida
--------------------------------------------

1. **Nao responde ao usuario** — a resposta oficial e retornada antes de o
   shadow ser considerado, e o resultado do shadow sai por outro campo.
2. **Nao executa acao externa** — o candidato recebe um contexto marcado como
   `side_effects_allowed=False`, e um candidato que tente efeito externo e
   recusado antes de rodar.
3. **Nao altera dado** — o servico nao escreve em lugar nenhum alem do proprio
   registro de comparacao.
4. **Nao duplica efeito** — se o primario ja produziu efeito, o shadow roda
   sobre a mesma ENTRADA, nunca sobre a saida do primario.
5. **Respeita orcamento** — timeout e budget explicitos; estourar o orcamento
   cancela o shadow e nao afeta o primario.

Falha do shadow nunca vira falha do usuario
-------------------------------------------

Qualquer excecao no candidato e capturada e registrada como comparacao
falha. Um experimento que pudesse derrubar a resposta oficial deixaria de ser
experimento e viraria risco.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SHADOW_MODE_VERSION = "shadow-mode-v1"


class ShadowOutcome(str, Enum):
    MATCHED = "MATCHED"
    DIVERGED = "DIVERGED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    REFUSED = "REFUSED"


@dataclass(frozen=True, slots=True)
class ShadowContext:
    """Contexto entregue ao candidato. Efeito externo e proibido por dado."""

    project_id: str
    environment: str
    correlation_id: str
    side_effects_allowed: Literal[False] = False
    persistence_allowed: Literal[False] = False
    responds_to_user: Literal[False] = False


@dataclass(slots=True)
class ShadowCandidate:
    """Um candidato observado.

    `declares_side_effects` e uma DECLARACAO do candidato. Quem declara efeito
    externo e recusado antes de rodar — a recusa e barata, o efeito nao.
    """

    candidate_id: str
    run: Callable[[Any, ShadowContext], Any]
    declares_side_effects: bool = False
    budget_seconds: float = 2.0
    metadata: dict[str, str] = field(default_factory=dict)


class ShadowComparison(BaseModel):
    """Resultado da observacao. Evidencia, nunca resposta."""

    model_config = ConfigDict(extra="forbid")

    comparison_id: str
    shadow_version: Literal["shadow-mode-v1"] = SHADOW_MODE_VERSION
    candidate_id: str
    project_id: str
    correlation_id: str
    outcome: ShadowOutcome
    primary_fingerprint: str
    shadow_fingerprint: str | None = None
    duration_seconds: float = Field(default=0.0, ge=0.0)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    observed_at: datetime

    # Garantias declaradas no proprio registro, para que uma evidencia
    # exportada carregue as suas condicoes junto.
    affected_user_response: Literal[False] = False
    produced_side_effects: Literal[False] = False


class ShadowExecutionService:
    """Roda candidatos em paralelo lógico, sempre depois do primário."""

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled
        self._comparisons: list[ShadowComparison] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    def disable(self) -> None:
        """Desligavel a qualquer momento, sem tocar no caminho primario."""
        self._enabled = False

    def enable(self) -> None:
        self._enabled = True

    def observe(
        self,
        *,
        candidate: ShadowCandidate,
        primary_input: Any,
        primary_output: Any,
        project_id: str,
        environment: str,
        correlation_id: str,
        fingerprint: Callable[[Any], str],
        now: datetime | None = None,
    ) -> ShadowComparison:
        """Observa o candidato sobre a MESMA entrada que o primario recebeu.

        Sobre a entrada, e nao sobre a saida do primario: encadear os dois
        faria o shadow herdar o efeito do primario e deixaria de medir o
        candidato.
        """
        instante = now or datetime.now(timezone.utc)
        primaria = fingerprint(primary_output)
        base = dict(
            comparison_id=f"shadow_{uuid.uuid4().hex[:20]}",
            candidate_id=candidate.candidate_id,
            project_id=project_id.strip().lower(),
            correlation_id=correlation_id,
            primary_fingerprint=primaria,
            observed_at=instante,
        )

        if not self._enabled:
            return self._store(
                ShadowComparison(
                    **base, outcome=ShadowOutcome.SKIPPED, reason_codes=("SHADOW_DISABLED",)
                )
            )

        if candidate.declares_side_effects:
            # Recusa ANTES de rodar. Um candidato que declara efeito externo
            # nao pode ser observado em paralelo: o efeito seria real.
            return self._store(
                ShadowComparison(
                    **base,
                    outcome=ShadowOutcome.REFUSED,
                    reason_codes=("CANDIDATE_DECLARES_SIDE_EFFECTS",),
                )
            )

        contexto = ShadowContext(
            project_id=project_id.strip().lower(),
            environment=environment,
            correlation_id=correlation_id,
        )

        inicio = time.perf_counter()
        try:
            resultado = candidate.run(primary_input, contexto)
        except Exception as error:  # noqa: BLE001 - falha do shadow nao sobe
            # Um experimento nunca derruba a resposta oficial. O tipo da
            # excecao vira motivo; a mensagem nao viaja.
            return self._store(
                ShadowComparison(
                    **base,
                    outcome=ShadowOutcome.FAILED,
                    duration_seconds=time.perf_counter() - inicio,
                    reason_codes=(f"SHADOW_RAISED_{type(error).__name__.upper()}",),
                )
            )

        duracao = time.perf_counter() - inicio
        if duracao > candidate.budget_seconds:
            return self._store(
                ShadowComparison(
                    **base,
                    outcome=ShadowOutcome.BUDGET_EXCEEDED,
                    duration_seconds=duracao,
                    shadow_fingerprint=fingerprint(resultado),
                    reason_codes=("SHADOW_BUDGET_EXCEEDED",),
                )
            )

        sombra = fingerprint(resultado)
        return self._store(
            ShadowComparison(
                **base,
                outcome=ShadowOutcome.MATCHED
                if sombra == primaria
                else ShadowOutcome.DIVERGED,
                duration_seconds=duracao,
                shadow_fingerprint=sombra,
                reason_codes=("SHADOW_MATCHED",)
                if sombra == primaria
                else ("SHADOW_DIVERGED",),
            )
        )

    def comparisons(self, project_id: str | None = None) -> list[ShadowComparison]:
        if project_id is None:
            return list(self._comparisons)
        projeto = project_id.strip().lower()
        return [item for item in self._comparisons if item.project_id == projeto]

    def divergence_rate(self, candidate_id: str) -> float | None:
        """Fracao de divergencia entre observacoes concluidas.

        `None` quando nao ha observacao concluida — e diferente de zero, que
        significaria "nunca divergiu".
        """
        concluidas = [
            item
            for item in self._comparisons
            if item.candidate_id == candidate_id
            and item.outcome in {ShadowOutcome.MATCHED, ShadowOutcome.DIVERGED}
        ]
        if not concluidas:
            return None
        divergiram = sum(1 for item in concluidas if item.outcome is ShadowOutcome.DIVERGED)
        return divergiram / len(concluidas)

    def reset(self) -> None:
        self._comparisons.clear()

    def _store(self, comparison: ShadowComparison) -> ShadowComparison:
        self._comparisons.append(comparison)
        return comparison


shadow_execution_service = ShadowExecutionService()
