"""Projeção do domínio Risk para a persistência própria (Stage R2).

Este módulo é a fronteira entre o objeto rico que o motor produz e o registro
enxuto que fica guardado. Ele existe para que a decisão "o que vai para o
banco" seja tomada em um lugar só, explicitamente, e não espalhada por quem
chama.

O que ele NÃO faz
-----------------

Não decide risco, não altera gate e não executa nada. Persistir é registro, e
registro que muda o que registra deixa de ser registro.

E não escreve quando a persistência está desligada. `off` é o default e
significa exatamente isso — o comportamento do motor com persistência desligada
é o mesmo de antes desta Stage, que é o que mantém a compatibilidade.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.modules.risk_engine.schemas import RiskSeverity
from app.modules.risk_engine.persistence_schemas import (
    PersistedRiskDimension,
    RiskAnalysisRecord,
    RiskHistorySlice,
    RiskOutcomeRecord,
)
from app.modules.risk_engine.repository import (
    RiskRecordConflictError,
    RiskRepository,
    RiskRepositoryConfigurationError,
    build_risk_repository,
    fingerprint_of,
    require_risk_repository,
    risk_persistence_mode,
)



# Ordem de gravidade, do menor para o maior. Existe porque a severidade
# agregada da analise nao e um campo do dominio: ela e derivada das dimensoes,
# e derivar significa escolher uma regra. A escolha aqui e a mais conservadora
# possivel — a analise vale pela sua pior dimensao, nao pela media.
_SEVERITY_ORDER: tuple[str, ...] = (
    RiskSeverity.INFO.value,
    RiskSeverity.LOW.value,
    RiskSeverity.MEDIUM.value,
    RiskSeverity.HIGH.value,
    RiskSeverity.CRITICAL.value,
)


def _aggregate_severity(dimensions: tuple[PersistedRiskDimension, ...]) -> str:
    """Severidade da analise = a pior dimensao observada.

    Media esconderia o caso perigoso: uma unica dimensao CRITICAL diluida entre
    cinco INFO viraria LOW, e o registro historico passaria a mentir sobre o
    que o motor tinha visto.
    """
    if not dimensions:
        return RiskSeverity.INFO.value
    return max(
        (item.severity for item in dimensions),
        key=lambda value: _SEVERITY_ORDER.index(value)
        if value in _SEVERITY_ORDER
        else 0,
    )


class RiskPersistenceService:
    """Grava e lê a história própria do Risk Engine."""

    def __init__(self) -> None:
        self._override: RiskRepository | None = None

    # -- repositório ------------------------------------------------------

    def set_repository(self, repository: RiskRepository | None) -> None:
        """Injeta um repositório (teste). `None` volta a resolver do ambiente."""
        self._override = repository

    def _repository(self) -> RiskRepository | None:
        if self._override is not None:
            return self._override
        return build_risk_repository()

    def enabled(self) -> bool:
        """A persistência própria está ligada?

        Exposto para que quem chama possa saber ANTES de agir, em vez de
        descobrir por exceção — a diferença entre "não guardei porque está
        desligado" e "falhei ao guardar" precisa continuar visível.
        """
        if self._override is not None:
            return True
        return risk_persistence_mode() != "off"

    # -- escrita ----------------------------------------------------------

    def record_analysis(self, analysis, *, now: datetime | None = None) -> bool:
        """Projeta e grava uma análise pré-execução.

        Devolve `False` quando a persistência está desligada OU quando o
        registro já existia idêntico. As duas situações têm em comum o que
        importa para quem chama: nada novo foi escrito.
        """
        if not self.enabled():
            return False
        record = self.project_analysis(analysis, now=now)
        return self._required().add_analysis(record)

    def record_outcome(self, outcome, *, now: datetime | None = None) -> bool:
        """Projeta e grava um resultado pós-execução."""
        if not self.enabled():
            return False
        record = self.project_outcome(outcome, now=now)
        return self._required().add_outcome(record)

    def _required(self) -> RiskRepository:
        if self._override is not None:
            return self._override
        return require_risk_repository()

    # -- projeção ---------------------------------------------------------

    @staticmethod
    def project_analysis(analysis, *, now: datetime | None = None) -> RiskAnalysisRecord:
        """Converte `PreExecutionRiskAnalysis` no registro persistido.

        Só entra o que é código ou número. `foundation`, `semantic_analysis`,
        `simulations` e `evidence` ficam de fora: são o raciocínio, não o fato,
        e é neles que texto vindo do consumidor poderia estar.
        """
        dimensions = tuple(
            PersistedRiskDimension(
                dimension=item.dimension.value,
                score=item.score,
                severity=item.severity.value,
            )
            for item in analysis.risk_dimensions
        )
        reason_codes = tuple(
            sorted({item.reason_code for item in analysis.deterministic_rules})
        )
        severity = _aggregate_severity(dimensions)
        payload = {
            "analysis_id": analysis.analysis_id,
            "project_id": analysis.project_id,
            "request_id": analysis.request_id,
            "severity": severity,
            "confidence": analysis.confidence,
            "uncertainty": analysis.uncertainty,
            "dimensions": [item.model_dump(mode="json") for item in dimensions],
            "reason_codes": list(reason_codes),
        }
        return RiskAnalysisRecord(
            analysis_id=analysis.analysis_id,
            project_id=analysis.project_id.strip().lower(),
            request_id=analysis.request_id,
            analysis_policy_version=analysis.policy_version,
            severity=severity,
            confidence=analysis.confidence,
            uncertainty=analysis.uncertainty,
            dimensions=dimensions,
            reason_codes=reason_codes,
            blast_radius_level=analysis.blast_radius.magnitude.value,
            fingerprint=fingerprint_of(payload),
            created_at=now or datetime.now(timezone.utc),
        )

    @staticmethod
    def project_outcome(outcome, *, now: datetime | None = None) -> RiskOutcomeRecord:
        """Converte `PostExecutionOutcome` no registro persistido.

        `execution_outcome_report`, `qa` e `operational_memory` ficam de fora:
        já têm dono — Report Memory e Operational Memory — e duplicá-los aqui
        criaria duas versões da mesma verdade.
        """
        comparison = outcome.comparison
        predicted = outcome.predicted_vs_actual
        payload = {
            "outcome_id": outcome.outcome_id,
            "project_id": outcome.project_id,
            "risk_analysis_id": outcome.risk_analysis_id,
            "contract_id": outcome.contract_id,
            "effective_gate": outcome.effective_gate.value,
            "status": outcome.status,
            "contract_valid": outcome.contract_valid,
            "actual_issue_codes": sorted(predicted.actual_issue_codes),
            "scope_deviation": sorted(comparison.scope_deviation),
        }
        return RiskOutcomeRecord(
            outcome_id=outcome.outcome_id,
            project_id=outcome.project_id.strip().lower(),
            risk_analysis_id=outcome.risk_analysis_id,
            contract_id=outcome.contract_id,
            evidence_id=outcome.evidence_id,
            outcome_policy_version=outcome.policy_version,
            effective_gate=outcome.effective_gate.value,
            status=outcome.status,
            contract_valid=outcome.contract_valid,
            predicted_dimensions=dict(predicted.predicted_dimensions),
            actual_issue_codes=tuple(sorted(predicted.actual_issue_codes)),
            predicted_risk_materialized=predicted.predicted_risk_materialized,
            unpredicted_issue_detected=predicted.unpredicted_issue_detected,
            scope_deviation=tuple(sorted(comparison.scope_deviation)),
            fingerprint=fingerprint_of(payload),
            created_at=now or datetime.now(timezone.utc),
        )

    # -- leitura ----------------------------------------------------------

    def history(self, project_id: str, *, limit: int = 100) -> RiskHistorySlice:
        """História própria do projeto. Levanta se a persistência estiver off.

        Devolver um recorte vazio seria pior: quem pergunta não distinguiria
        "não há histórico" de "não há onde guardar histórico", e as duas coisas
        levam a decisões diferentes.
        """
        return self._required().history(project_id.strip().lower(), limit=limit)

    def analysis(self, project_id: str, analysis_id: str) -> RiskAnalysisRecord | None:
        return self._required().get_analysis(project_id.strip().lower(), analysis_id)

    def outcome(self, project_id: str, outcome_id: str) -> RiskOutcomeRecord | None:
        return self._required().get_outcome(project_id.strip().lower(), outcome_id)

    def reset(self) -> None:
        """Limpa o store atual. Silencioso quando não há store configurado."""
        try:
            self._required().clear()
        except RiskRepositoryConfigurationError:
            return


__all__ = [
    "RiskPersistenceService",
    "RiskRecordConflictError",
    "risk_persistence_service",
]

risk_persistence_service = RiskPersistenceService()
