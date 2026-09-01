"""Persistência própria do Risk Engine (Stage R2).

O problema que este módulo resolve
-----------------------------------

O baseline R0 registrou como P1 que o Risk Engine não tinha onde guardar a
própria história: ele lia de `report_memory` e `operational_memory`. A
consequência prática é que `PEDROCORE_REPORT_MEMORY_PERSISTENCE=off` decidia,
em silêncio, se o motor de risco tinha ou não histórico — uma variável de outro
domínio determinando o comportamento deste.

Com repositório próprio, o Risk Engine passa a ter uma fonte de verdade do seu
domínio. Report Memory e Operational Memory continuam existindo e continuam
recebendo o que sempre receberam; elas deixam de ser a **única** origem.

    POST EXECUTION
        ├── Risk Repository      fonte de verdade do domínio Risk
        ├── Report Memory        projeção operacional/relatório
        └── Operational Memory   padrão operacional aprendido

Isolamento de projeto é chave, não filtro
------------------------------------------

Toda leitura recebe `project_id` e o usa na consulta. Não existe `get(id)`
seguido de `if record.project_id == caller.project_id` — esse desenho já
carregou o dado do outro projeto para a memória antes de decidir, e basta
alguém esquecer o `if` uma vez para virar vazamento.

Fail-closed
-----------

Modo `postgresql` sem URL, ou banco indisponível, **levanta**. Não cai para
memória. Um histórico de risco que silenciosamente vira efêmero faria um `BLOCK`
baseado em histórico se comportar de forma diferente sem ninguém perceber — e a
decisão de risco é exatamente onde isso não pode acontecer.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Protocol, runtime_checkable

import psycopg
from psycopg.types.json import Jsonb

from app.modules.risk_engine.persistence_schemas import (
    RiskAnalysisRecord,
    RiskHistorySlice,
    RiskOutcomeRecord,
)

FLAG_RISK_PERSISTENCE = "PEDROCORE_RISK_PERSISTENCE"
FLAG_RISK_DATABASE_URL = "PEDROCORE_RISK_DATABASE_URL"

MODE_OFF = "off"
MODE_MEMORY = "memory"
MODE_POSTGRESQL = "postgresql"
VALID_MODES = {MODE_OFF, MODE_MEMORY, MODE_POSTGRESQL}

# Teto de leitura. Historico de risco cresce sem limite natural, e uma consulta
# sem teto acabaria carregando anos de registro para responder uma pergunta
# sobre as ultimas execucoes.
MAX_HISTORY_RECORDS = 500


class RiskRepositoryError(RuntimeError):
    """Falha operacional do repositório de risco."""


class RiskRepositoryConfigurationError(RiskRepositoryError):
    """Configuração ausente, inválida ou incoerente. Sempre fail-closed."""


class RiskRecordConflictError(RiskRepositoryError):
    """Mesmo id, conteúdo diferente.

    Separado da duplicata comum porque as duas situações são opostas: replay
    idêntico é ruído esperado e vira no-op; mesmo id com conteúdo diferente é
    sinal de bug ou de adulteração, e sobrescrever apagaria o registro original
    sem que ninguém soubesse.
    """

    def __init__(self, record_id: str) -> None:
        super().__init__(record_id)
        self.record_id = record_id


def fingerprint_of(payload: object) -> str:
    """Fingerprint estável do conteúdo. Derivado pelo servidor, sempre."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()


@runtime_checkable
class RiskRepository(Protocol):
    """Contrato do armazenamento de risco.

    `Protocol` e não classe base: o serviço depende da forma, não da herança, e
    um teste pode oferecer a sua própria implementação sem herdar nada.
    """

    def add_analysis(self, record: RiskAnalysisRecord) -> bool:
        """`False` quando já existia idêntico — duplicata, não erro."""
        ...

    def get_analysis(self, project_id: str, analysis_id: str) -> RiskAnalysisRecord | None: ...

    def add_outcome(self, record: RiskOutcomeRecord) -> bool: ...

    def get_outcome(self, project_id: str, outcome_id: str) -> RiskOutcomeRecord | None: ...

    def history(self, project_id: str, *, limit: int = 100) -> RiskHistorySlice: ...

    def count(self, project_id: str) -> int: ...

    def clear(self) -> None: ...


class InMemoryRiskRepository:
    """Store em processo. Modo `memory`, explícito, e uso em teste."""

    def __init__(self) -> None:
        self._analyses: dict[tuple[str, str], RiskAnalysisRecord] = {}
        self._outcomes: dict[tuple[str, str], RiskOutcomeRecord] = {}

    # -- escrita ----------------------------------------------------------

    def add_analysis(self, record: RiskAnalysisRecord) -> bool:
        key = (record.project_id, record.analysis_id)
        existing = self._analyses.get(key)
        if existing is not None:
            if existing.fingerprint != record.fingerprint:
                raise RiskRecordConflictError(record.analysis_id)
            return False
        self._analyses[key] = record.model_copy(deep=True)
        return True

    def add_outcome(self, record: RiskOutcomeRecord) -> bool:
        key = (record.project_id, record.outcome_id)
        existing = self._outcomes.get(key)
        if existing is not None:
            if existing.fingerprint != record.fingerprint:
                raise RiskRecordConflictError(record.outcome_id)
            return False
        self._outcomes[key] = record.model_copy(deep=True)
        return True

    # -- leitura ----------------------------------------------------------

    def get_analysis(self, project_id: str, analysis_id: str) -> RiskAnalysisRecord | None:
        found = self._analyses.get((project_id, analysis_id))
        return found.model_copy(deep=True) if found else None

    def get_outcome(self, project_id: str, outcome_id: str) -> RiskOutcomeRecord | None:
        found = self._outcomes.get((project_id, outcome_id))
        return found.model_copy(deep=True) if found else None

    def history(self, project_id: str, *, limit: int = 100) -> RiskHistorySlice:
        window = min(max(limit, 1), MAX_HISTORY_RECORDS)
        analyses = sorted(
            (item.model_copy(deep=True) for (p, _), item in self._analyses.items() if p == project_id),
            key=lambda item: (item.created_at, item.analysis_id),
        )
        outcomes = sorted(
            (item.model_copy(deep=True) for (p, _), item in self._outcomes.items() if p == project_id),
            key=lambda item: (item.created_at, item.outcome_id),
        )
        return RiskHistorySlice(
            project_id=project_id,
            analyses=tuple(analyses[-window:]),
            outcomes=tuple(outcomes[-window:]),
        )

    def count(self, project_id: str) -> int:
        return sum(1 for (p, _) in self._analyses if p == project_id) + sum(
            1 for (p, _) in self._outcomes if p == project_id
        )

    def clear(self) -> None:
        self._analyses.clear()
        self._outcomes.clear()


_INSERT_ANALYSIS = """
INSERT INTO pedrocore_risk_analyses (
    analysis_id, project_id, request_id, analysis_policy_version, severity,
    confidence, uncertainty, blast_radius_level, reason_codes, dimensions,
    fingerprint, created_at, policy_version
) VALUES (
    %(analysis_id)s, %(project_id)s, %(request_id)s, %(analysis_policy_version)s,
    %(severity)s, %(confidence)s, %(uncertainty)s, %(blast_radius_level)s,
    %(reason_codes)s, %(dimensions)s, %(fingerprint)s, %(created_at)s,
    %(policy_version)s
)
ON CONFLICT (project_id, analysis_id) DO NOTHING
"""

_INSERT_OUTCOME = """
INSERT INTO pedrocore_risk_outcomes (
    outcome_id, project_id, risk_analysis_id, contract_id, evidence_id,
    outcome_policy_version, effective_gate, status, contract_valid,
    predicted_risk_materialized, unpredicted_issue_detected,
    predicted_dimensions, actual_issue_codes, scope_deviation,
    fingerprint, created_at, policy_version
) VALUES (
    %(outcome_id)s, %(project_id)s, %(risk_analysis_id)s, %(contract_id)s,
    %(evidence_id)s, %(outcome_policy_version)s, %(effective_gate)s, %(status)s,
    %(contract_valid)s, %(predicted_risk_materialized)s,
    %(unpredicted_issue_detected)s, %(predicted_dimensions)s,
    %(actual_issue_codes)s, %(scope_deviation)s, %(fingerprint)s,
    %(created_at)s, %(policy_version)s
)
ON CONFLICT (project_id, outcome_id) DO NOTHING
"""

_ANALYSIS_COLUMNS = """
    analysis_id, project_id, request_id, analysis_policy_version, severity,
    confidence, uncertainty, blast_radius_level, reason_codes, dimensions,
    fingerprint, created_at, policy_version
"""

_OUTCOME_COLUMNS = """
    outcome_id, project_id, risk_analysis_id, contract_id, evidence_id,
    outcome_policy_version, effective_gate, status, contract_valid,
    predicted_risk_materialized, unpredicted_issue_detected,
    predicted_dimensions, actual_issue_codes, scope_deviation,
    fingerprint, created_at, policy_version
"""


def _analysis_from_row(row: tuple) -> RiskAnalysisRecord:
    return RiskAnalysisRecord(
        analysis_id=row[0],
        project_id=row[1],
        request_id=row[2],
        analysis_policy_version=row[3],
        severity=row[4],
        confidence=row[5],
        uncertainty=row[6],
        blast_radius_level=row[7],
        reason_codes=tuple(row[8] or ()),
        dimensions=tuple(row[9] or ()),
        fingerprint=row[10],
        created_at=row[11],
        policy_version=row[12],
    )


def _outcome_from_row(row: tuple) -> RiskOutcomeRecord:
    return RiskOutcomeRecord(
        outcome_id=row[0],
        project_id=row[1],
        risk_analysis_id=row[2],
        contract_id=row[3],
        evidence_id=row[4],
        outcome_policy_version=row[5],
        effective_gate=row[6],
        status=row[7],
        contract_valid=row[8],
        predicted_risk_materialized=row[9],
        unpredicted_issue_detected=row[10],
        predicted_dimensions=row[11] or {},
        actual_issue_codes=tuple(row[12] or ()),
        scope_deviation=tuple(row[13] or ()),
        fingerprint=row[14],
        created_at=row[15],
        policy_version=row[16],
    )


class PostgreSQLRiskRepository:
    """Store PostgreSQL. Isolamento de projeto é chave primária composta."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self) -> psycopg.Connection:
        try:
            return psycopg.connect(self._database_url, connect_timeout=5)
        except psycopg.Error as error:
            # Banco indisponivel NAO vira memoria. O chamador precisa saber que
            # a decisao de risco esta sem historico.
            raise RiskRepositoryError(
                "Risk Repository PostgreSQL indisponível; nenhum fallback aplicado."
            ) from error

    def add_analysis(self, record: RiskAnalysisRecord) -> bool:
        existing = self.get_analysis(record.project_id, record.analysis_id)
        if existing is not None:
            if existing.fingerprint != record.fingerprint:
                raise RiskRecordConflictError(record.analysis_id)
            return False
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                _INSERT_ANALYSIS,
                {
                    "analysis_id": record.analysis_id,
                    "project_id": record.project_id,
                    "request_id": record.request_id,
                    "analysis_policy_version": record.analysis_policy_version,
                    "severity": record.severity,
                    "confidence": record.confidence,
                    "uncertainty": record.uncertainty,
                    "blast_radius_level": record.blast_radius_level,
                    "reason_codes": Jsonb(list(record.reason_codes)),
                    "dimensions": Jsonb(
                        [item.model_dump(mode="json") for item in record.dimensions]
                    ),
                    "fingerprint": record.fingerprint,
                    "created_at": record.created_at,
                    "policy_version": record.policy_version,
                },
            )
            return cursor.rowcount == 1

    def add_outcome(self, record: RiskOutcomeRecord) -> bool:
        existing = self.get_outcome(record.project_id, record.outcome_id)
        if existing is not None:
            if existing.fingerprint != record.fingerprint:
                raise RiskRecordConflictError(record.outcome_id)
            return False
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                _INSERT_OUTCOME,
                {
                    "outcome_id": record.outcome_id,
                    "project_id": record.project_id,
                    "risk_analysis_id": record.risk_analysis_id,
                    "contract_id": record.contract_id,
                    "evidence_id": record.evidence_id,
                    "outcome_policy_version": record.outcome_policy_version,
                    "effective_gate": record.effective_gate,
                    "status": record.status,
                    "contract_valid": record.contract_valid,
                    "predicted_risk_materialized": record.predicted_risk_materialized,
                    "unpredicted_issue_detected": record.unpredicted_issue_detected,
                    "predicted_dimensions": Jsonb(dict(record.predicted_dimensions)),
                    "actual_issue_codes": Jsonb(list(record.actual_issue_codes)),
                    "scope_deviation": Jsonb(list(record.scope_deviation)),
                    "fingerprint": record.fingerprint,
                    "created_at": record.created_at,
                    "policy_version": record.policy_version,
                },
            )
            return cursor.rowcount == 1

    def get_analysis(self, project_id: str, analysis_id: str) -> RiskAnalysisRecord | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_ANALYSIS_COLUMNS} FROM pedrocore_risk_analyses "
                "WHERE project_id = %s AND analysis_id = %s",
                (project_id, analysis_id),
            )
            row = cursor.fetchone()
            return _analysis_from_row(row) if row else None

    def get_outcome(self, project_id: str, outcome_id: str) -> RiskOutcomeRecord | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_OUTCOME_COLUMNS} FROM pedrocore_risk_outcomes "
                "WHERE project_id = %s AND outcome_id = %s",
                (project_id, outcome_id),
            )
            row = cursor.fetchone()
            return _outcome_from_row(row) if row else None

    def history(self, project_id: str, *, limit: int = 100) -> RiskHistorySlice:
        window = min(max(limit, 1), MAX_HISTORY_RECORDS)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {_ANALYSIS_COLUMNS} FROM pedrocore_risk_analyses "
                "WHERE project_id = %s ORDER BY created_at DESC, analysis_id DESC LIMIT %s",
                (project_id, window),
            )
            analyses = [_analysis_from_row(row) for row in cursor.fetchall()]
            cursor.execute(
                f"SELECT {_OUTCOME_COLUMNS} FROM pedrocore_risk_outcomes "
                "WHERE project_id = %s ORDER BY created_at DESC, outcome_id DESC LIMIT %s",
                (project_id, window),
            )
            outcomes = [_outcome_from_row(row) for row in cursor.fetchall()]
        return RiskHistorySlice(
            project_id=project_id,
            analyses=tuple(reversed(analyses)),
            outcomes=tuple(reversed(outcomes)),
        )

    def count(self, project_id: str) -> int:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT (SELECT COUNT(*) FROM pedrocore_risk_analyses WHERE project_id = %s)"
                " + (SELECT COUNT(*) FROM pedrocore_risk_outcomes WHERE project_id = %s)",
                (project_id, project_id),
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def clear(self) -> None:
        """Apaga tudo. Existe para QA isolado, nunca para produção."""
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM pedrocore_risk_outcomes")
            cursor.execute("DELETE FROM pedrocore_risk_analyses")


def risk_persistence_mode() -> str:
    """Modo efetivo. Chave PRÓPRIA do Risk Engine, não a do Report Memory.

    Essa independência é o ponto do Stage R2: qual variável decide se o motor
    de risco tem histórico não pode ser a de outro domínio.
    """
    raw = (os.environ.get(FLAG_RISK_PERSISTENCE) or MODE_OFF).strip().lower()
    if raw not in VALID_MODES:
        raise RiskRepositoryConfigurationError(
            f"{FLAG_RISK_PERSISTENCE}='{raw}' é inválido; use off, memory ou postgresql."
        )
    return raw


_MEMORY_SINGLETON = InMemoryRiskRepository()


def build_risk_repository() -> RiskRepository | None:
    """Constrói o repositório conforme a configuração.

    Devolve `None` somente no modo `off`, que é o default e significa
    "desabilitado" — não "em memória". Quem precisa do repositório usa
    `require_risk_repository`.
    """
    mode = risk_persistence_mode()
    if mode == MODE_MEMORY:
        return _MEMORY_SINGLETON
    if mode == MODE_POSTGRESQL:
        database_url = (os.environ.get(FLAG_RISK_DATABASE_URL) or "").strip()
        if not database_url:
            raise RiskRepositoryConfigurationError(
                f"{FLAG_RISK_DATABASE_URL} é obrigatória no modo postgresql; "
                "o Risk Engine não reaproveita a URL de outro domínio por conta própria."
            )
        return PostgreSQLRiskRepository(database_url)
    return None


def require_risk_repository() -> RiskRepository:
    """Repositório obrigatório. Levanta quando desabilitado."""
    repository = build_risk_repository()
    if repository is None:
        raise RiskRepositoryConfigurationError(
            "Risk Repository desabilitado; nenhum fallback em memória foi aplicado."
        )
    return repository
