"""Learning Source Contract V1.

A distincao que este contrato existe para proteger
--------------------------------------------------

    Operational Source  !=  Training Candidate

Uma fonte operacional e algo que aconteceu e que PODERIA, um dia, virar exemplo
de treino. Um Training Candidate e algo que ja passou por elegibilidade,
privacidade, proveniencia e autorizacao. A distancia entre os dois e a
governanca inteira do Learning Plane.

Este contrato transporta apenas o primeiro. Submeter uma fonte NAO concede:

  - eligibility;
  - authorization;
  - candidate status;
  - dataset membership;
  - readiness;
  - canonical status.

Toda promocao continua pertencendo ao Learning Plane, que reavalia por conta
propria a cada candidato. Uma fonte submetida hoje pode ser recusada amanha
porque a politica mudou — e isso e correto.

`automatic_collection` continua `false`
---------------------------------------

Submeter uma fonte e um ato explicito de um produtor autorizado. Nao existe, e
nao deve existir, adapter interno que va buscar fonte na base de um consumidor:
isso exigiria que o PedroCore alcancasse dados que a fronteira proibe. Este
contrato e o caminho de entrada explicito, e nao um gatilho de coleta.

Por que so conteudo derivado
----------------------------

`derived_content_only` e `Literal[True]`. Nao e uma flag que o produtor escolhe:
e um tipo que faz o Pydantic recusar `False`. Conteudo bruto — transcricao,
diario, midia, log integral — nao entra por este contrato em nenhuma
circunstancia, e a recusa acontece antes de qualquer regra de negocio.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.universal_contracts.versioning import LEARNING_SOURCE_V1

ShortText = Annotated[str, Field(min_length=1, max_length=128)]
Signature = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class LearningSourceKind(str, Enum):
    """Natureza da fonte operacional oferecida.

    Note que estes nomes descrevem o QUE a fonte e, nunca de quem ela veio. Um
    consumidor novo com o mesmo tipo de fonte reutiliza o mesmo valor — nao se
    acrescenta um membro por integrador.
    """

    QUALITY_EVIDENCE = "quality_evidence"
    EXECUTION_OUTCOME = "execution_outcome"
    INTERACTION_OUTCOME = "interaction_outcome"
    OPERATIONAL_PATTERN = "operational_pattern"
    RISK_ANALYSIS = "risk_analysis"
    REPORT_SNAPSHOT = "report_snapshot"
    HUMAN_FEEDBACK = "human_feedback"


class ProducerAssertedOutcome(str, Enum):
    """Como o produtor classificou o desfecho — alegacao, nao veredito.

    O prefixo `producer_asserted_` no campo que usa este enum e deliberado: ele
    marca no proprio nome que isto e o que o cliente DIZ, e sobrevive a
    fronteira de autoridade justamente por nao se apresentar como sentenca.
    """

    SUCCESSFUL = "successful"
    FAILED = "failed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class SourceProvenanceV1(BaseModel):
    """De onde a fonte veio, sem dizer de QUEM veio.

    Nao ha `user_id`, `session_id` nem identificador pessoal legivel: a
    rastreabilidade ate a pessoa fica no consumidor, do lado que tem base legal
    para mante-la. O PedroCore recebe o suficiente para auditar a origem e
    nada alem disso.
    """

    model_config = ConfigDict(extra="forbid")

    source_kind: LearningSourceKind
    source_schema_version: ShortText
    producer_policy_version: ShortText
    produced_at: datetime
    content_signature: Signature
    run_id: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def _produced_at_requires_timezone(self) -> SourceProvenanceV1:
        if self.produced_at.tzinfo is None:
            raise ValueError("produced_at deve incluir timezone")
        return self

    @model_validator(mode="after")
    def _policy_version_must_be_meaningful(self) -> SourceProvenanceV1:
        """Proveniencia sem versao de politica nao e proveniencia.

        "unknown" e uma resposta pior do que a ausencia do campo: parece
        preenchido e nao permite reconstruir sob qual regra a fonte nasceu.
        """
        if self.producer_policy_version.strip().lower() in {"unknown", "none", "n/a", "-"}:
            raise ValueError(
                "producer_policy_version precisa identificar a politica real do produtor"
            )
        return self


class TrainingConsentAssertionV1(BaseModel):
    """Consentimento de TREINO afirmado pelo produtor.

    Isto NAO e `DataUseAuthorization`. E a alegacao de que a pessoa dona do dado
    consentiu com uso para treino, do lado do consumidor. O PedroCore registra a
    alegacao e continua exigindo sua propria autorizacao antes de qualquer
    promocao a candidato: consentimento do titular e condicao necessaria, nunca
    suficiente.
    """

    model_config = ConfigDict(extra="forbid")

    producer_asserted_consent: Literal[True]
    consent_version: ShortText
    asserted_at: datetime

    @model_validator(mode="after")
    def _asserted_at_requires_timezone(self) -> TrainingConsentAssertionV1:
        if self.asserted_at.tzinfo is None:
            raise ValueError("asserted_at deve incluir timezone")
        return self


class LearningSourceV1(BaseModel):
    """Fonte operacional oferecida ao Learning Plane — nunca um candidato.

    Ausencia de campos e parte do contrato: nao ha `eligibility`, `authorized`,
    `candidate_id`, `lifecycle`, `training_purpose` nem `quality_score`. Todos
    pertencem ao PedroCore, e tenta-los faz a fronteira de autoridade recusar a
    requisicao inteira.
    """

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["pedrocore-learning-source/v1"] = LEARNING_SOURCE_V1
    source_id: ShortText
    provenance: SourceProvenanceV1
    # Tipo, e nao flag: o Pydantic recusa `False` antes de qualquer regra.
    derived_content_only: Literal[True] = True
    producer_asserted_outcome: ProducerAssertedOutcome
    training_consent: TrainingConsentAssertionV1 | None = None
    # Conteudo derivado e minimizado. Numeros e rotulos curtos, nunca texto
    # livre do titular: o limite de tamanho existe para que "derivado" nao vire
    # um lugar onde conteudo bruto cabe.
    derived_features: dict[str, float | int | bool | str] = Field(default_factory=dict)
    summary: str | None = Field(default=None, max_length=1024)

    @model_validator(mode="after")
    def _derived_features_must_stay_minimal(self) -> LearningSourceV1:
        if len(self.derived_features) > 64:
            raise ValueError("derived_features excede o maximo de 64 entradas")
        for key, value in self.derived_features.items():
            if len(key) > 64:
                raise ValueError(f"chave de derived_features longa demais: {key[:32]}...")
            if isinstance(value, str) and len(value) > 256:
                raise ValueError(
                    f"valor textual de '{key}' excede 256 caracteres; "
                    "conteudo derivado nao transporta texto livre"
                )
        return self

    @model_validator(mode="after")
    def _provenance_kind_matches_consent_requirement(self) -> LearningSourceV1:
        """Snapshot de relatorio e feedback humano exigem consentimento afirmado.

        Sao as duas origens em que o dado nasce de uma pessoa, e nao de uma
        maquina executando uma tarefa. Sem a afirmacao de consentimento a fonte
        nem chega a ser avaliada.
        """
        requires_consent = {
            LearningSourceKind.REPORT_SNAPSHOT,
            LearningSourceKind.HUMAN_FEEDBACK,
        }
        if self.provenance.source_kind in requires_consent and self.training_consent is None:
            raise ValueError(
                f"fonte '{self.provenance.source_kind.value}' exige "
                "training_consent afirmado pelo produtor"
            )
        return self
