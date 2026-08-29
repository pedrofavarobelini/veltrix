"""Quality Evidence Contract — QEC V1.

Por que QEC nao e um quality score
----------------------------------

A tentacao obvia seria deixar o produtor enviar `quality_score: 100`. Seria
simples, e seria inutil: o numero passaria a valer o que vale a boa-fe de quem
o enviou, e duas suites de qualidade muito diferentes produziriam o mesmo 100.

QEC transporta **fato observavel e conferivel** — quantos testes rodaram,
quantos passaram, em que ambiente, com que referencia. O julgamento sobre o que
esses fatos significam pertence ao PedroCore, que pode aplicar politica propria,
comparar com historico e mudar de opiniao sem pedir nada ao produtor.

A separacao esta no vocabulario e e verificada: campos aqui descrevem
observacao (`total`, `passed`, `status`, `observed_at`). Emitir sentenca
(`quality_score`, `eligibility`) e recusado pela fronteira de autoridade em
`authority.py`.

Consistencia aritmetica
-----------------------

Um relatorio que diz "10 testes, 7 passaram, 2 falharam, 2 pularam" nao e um
relatorio ruim: e um relatorio impossivel. Aceita-lo tornaria o PedroCore
incapaz de distinguir dado real de dado inventado, entao ele e recusado.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.universal_contracts.versioning import QUALITY_EVIDENCE_V1

ShortText = Annotated[str, Field(min_length=1, max_length=128)]
Signature = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class EvidenceOutcome(str, Enum):
    """Resultado observado de uma execucao de qualidade."""

    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    ERRORED = "errored"


class ObservedSeverity(str, Enum):
    """Severidade tal como o produtor a observou — nao como o PedroCore a julga."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceEnvironment(str, Enum):
    """Onde a evidencia foi produzida.

    Producao e sempre explicita: nao existe wildcard que a inclua por descuido.
    """

    LOCAL = "local"
    DEVELOPMENT = "development"
    TEST = "test"
    CI = "ci"
    STAGING = "staging"
    PRODUCTION = "production"


class EvidenceReference(BaseModel):
    """Ponteiro para um artefato, sem transportar o artefato.

    O PedroCore nao le repositorio nem storage do consumidor. A referencia
    existe para auditoria posterior do lado de quem tem base legal para guardar
    o conteudo — por isso `locator` e um identificador opaco, e nao um caminho
    que alguem seria tentado a abrir.
    """

    model_config = ConfigDict(extra="forbid")

    reference_id: ShortText
    kind: Literal["report", "log", "artifact", "commit", "pipeline", "testcase"]
    locator: str = Field(..., min_length=1, max_length=512)
    content_signature: Signature | None = None


class TestCaseObservation(BaseModel):
    """Um caso observado. Sem stack trace e sem payload: fato, nao dump."""

    model_config = ConfigDict(extra="forbid")

    case_id: ShortText
    outcome: EvidenceOutcome
    duration_ms: float | None = Field(default=None, ge=0.0, le=86_400_000.0)
    observed_severity: ObservedSeverity | None = None


class SuiteObservation(BaseModel):
    """Contagens observadas de uma suite, aritmeticamente coerentes."""

    model_config = ConfigDict(extra="forbid")

    suite_id: ShortText
    outcome: EvidenceOutcome
    total: int = Field(..., ge=0, le=1_000_000)
    passed: int = Field(default=0, ge=0, le=1_000_000)
    failed: int = Field(default=0, ge=0, le=1_000_000)
    skipped: int = Field(default=0, ge=0, le=1_000_000)
    cases: tuple[TestCaseObservation, ...] = Field(default_factory=tuple, max_length=500)

    @model_validator(mode="after")
    def _counts_must_add_up(self) -> SuiteObservation:
        if self.passed + self.failed + self.skipped != self.total:
            raise ValueError(
                "contagens inconsistentes: passed + failed + skipped deve ser igual a total"
            )
        if self.outcome is EvidenceOutcome.PASSED and self.failed > 0:
            raise ValueError("suite declarada 'passed' nao pode registrar falhas")
        return self


class QualityEvidenceV1(BaseModel):
    """Evidencia de qualidade universal, independente de projeto.

    Nao ha campo de score, de aprovacao ou de elegibilidade — por construcao.
    O que o PedroCore conclui a partir daqui e derivado dele, e vive no Runtime
    Plane, nao neste contrato.
    """

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["pedrocore-quality-evidence/v1"] = QUALITY_EVIDENCE_V1
    evidence_id: ShortText
    outcome: EvidenceOutcome
    environment: EvidenceEnvironment
    observed_at: datetime
    suites: tuple[SuiteObservation, ...] = Field(default_factory=tuple, max_length=100)
    references: tuple[EvidenceReference, ...] = Field(default_factory=tuple, max_length=50)
    observed_severity: ObservedSeverity | None = None
    summary: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def _observed_at_requires_timezone(self) -> QualityEvidenceV1:
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at deve incluir timezone")
        return self

    @model_validator(mode="after")
    def _outcome_must_match_suites(self) -> QualityEvidenceV1:
        """Um veredito global 'passed' com suite falhando e contradicao.

        Deixar passar permitiria ao produtor enterrar uma falha em uma suite e
        anunciar sucesso no topo — exatamente o tipo de julgamento que este
        contrato existe para nao aceitar.
        """
        if self.outcome is EvidenceOutcome.PASSED and any(
            suite.outcome is EvidenceOutcome.FAILED or suite.failed > 0
            for suite in self.suites
        ):
            raise ValueError(
                "outcome 'passed' contradiz suite com falha observada"
            )
        return self

    def total_observed_cases(self) -> int:
        """Total observado, somado pelo PedroCore e nao aceito do produtor."""
        return sum(suite.total for suite in self.suites)
