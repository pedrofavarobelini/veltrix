"""Project Capability Manifest V1.

Por que este modulo existe
--------------------------

A Era 1 encontrou o core generico decidindo por NOME de consumidor:

    if caller.project_id == "elyra":
    if data.project.project_id == "finguard":

O problema nao e estetico. Um core que conhece nomes precisa ser editado toda
vez que um consumidor entra, e cada `if` novo e um lugar onde alguem pode
enganar-se sobre qual projeto recebe qual privilegio. A regra fica espalhada
pelo motor em vez de declarada em um lugar auditavel.

O manifesto inverte isso: o PedroCore deixa de perguntar **quem e voce** e passa
a perguntar **o que voce declara saber fazer**. O core testa capacidade; o
registro guarda o nome.

O que o manifesto NAO faz
-------------------------

Ele nao concede autorizacao de treinamento. Declarar a capability
`LEARNING_SOURCE` significa "sei produzir fonte de aprendizado", e nao "estou
autorizado a treinar". Autorizacao de treino continua sendo decisao do Learning
Plane, avaliada por `DataUseAuthorization` a cada candidato — nunca herdada de
um manifesto.

Ele tambem nao concede provider real, nao amplia `allowed_tasks` e nao substitui
a matriz de autorizacao: e uma DECLARACAO de capacidade, cruzada com politica,
e nao uma concessao.

Capability desconhecida
-----------------------

Fail-closed. Uma capability que este servidor nao conhece nao e ignorada nem
tratada como inofensiva: a validacao a recusa nomeando-a. Aceitar em silencio
faria um consumidor acreditar que negociou algo que o servidor nunca entendeu.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.universal_contracts.versioning import (
    CAPABILITY_MANIFEST_V1,
    PAYLOAD_CONTRACT_VERSIONS,
)

ShortText = Annotated[str, Field(min_length=1, max_length=128)]


class ProjectCapability(str, Enum):
    """O que um consumidor declara ser capaz de produzir ou consumir.

    Derivadas do codigo real: cada uma corresponde a um fluxo que ja existe no
    PedroCore, e nao a uma ambicao de roadmap. Uma capability sem fluxo
    correspondente seria uma promessa que o servidor nao sabe cumprir.
    """

    # Consome o assistente conversacional (`/api/chat`, `/api/orchestrate`).
    ASSISTANT = "assistant"
    # Produz evidencia de QA verificavel (QEC V1).
    QUALITY_EVIDENCE = "quality_evidence"
    # Produz resultado de execucao (Execution Outcome V1).
    EXECUTION_OUTCOME = "execution_outcome"
    # Produz relatorio estruturado de inteligencia (Report Intelligence).
    REPORT_INTELLIGENCE = "report_intelligence"
    # Produz sinal de aceitacao/rejeicao de resposta.
    INTERACTION_OUTCOME = "interaction_outcome"
    # Produz fonte operacional candidata a aprendizado (Learning Source V1).
    LEARNING_SOURCE = "learning_source"
    # Produz analise de risco pre-execucao.
    RISK_ANALYSIS = "risk_analysis"
    # Referencia artefatos por payload (nunca leitura de repositorio).
    ARTIFACT_REFERENCE = "artifact_reference"


class ProducerTrait(str, Enum):
    """Propriedades operacionais declaradas, tipadas em vez de boolean soup.

    `ProjectContext` ja carregava `read_only`, `can_execute_commands` e
    `can_write_files` como tres booleanos independentes — combinaveis em oito
    estados, dos quais varios sao incoerentes (`read_only` com `can_write_files`).
    Um conjunto de traits nomeados so representa o que faz sentido.
    """

    # O consumidor envia a mesma requisicao mais de uma vez sob a mesma chave e
    # espera deduplicacao governada em vez de efeito repetido.
    IDEMPOTENT_SUBMISSION = "idempotent_submission"
    # O consumidor e um sistema externo que o PedroCore nunca deve modificar.
    EXTERNALLY_OWNED = "externally_owned"
    # O consumidor exige correlacao explicita em toda requisicao.
    REQUIRES_CORRELATION = "requires_correlation"


class CapabilityDeclaration(BaseModel):
    """Uma capacidade declarada e as versoes de contrato que a sustentam."""

    model_config = ConfigDict(extra="forbid")

    capability: ProjectCapability
    contract_versions: tuple[str, ...] = Field(default_factory=tuple, max_length=16)

    @model_validator(mode="after")
    def _contract_versions_must_be_known(self) -> CapabilityDeclaration:
        unknown = [
            version
            for version in self.contract_versions
            if version not in PAYLOAD_CONTRACT_VERSIONS
        ]
        if unknown:
            raise ValueError(
                "contract_versions desconhecidas para esta capability: "
                f"{sorted(unknown)}"
            )
        return self


class ProjectCapabilityManifestV1(BaseModel):
    """Manifesto declarativo de um consumidor.

    O `project_id` identifica; ele nao autoriza. Toda decisao do core generico
    deve consultar `capabilities` e `traits`, jamais comparar `project_id` com
    um literal.
    """

    model_config = ConfigDict(extra="forbid")

    manifest_version: Literal["pedrocore-capability-manifest/v1"] = CAPABILITY_MANIFEST_V1
    project_id: ShortText
    display_name: ShortText
    producer_id: str | None = Field(default=None, max_length=128)
    capabilities: tuple[CapabilityDeclaration, ...] = Field(
        default_factory=tuple, max_length=32
    )
    traits: frozenset[ProducerTrait] = Field(default_factory=frozenset)
    allowed_tasks: tuple[str, ...] = Field(default_factory=tuple, max_length=64)
    # Recursos externos que este consumidor possui e que o PedroCore nunca deve
    # ler, escrever ou navegar. Substitui denylists por nome no core.
    protected_resource_markers: tuple[str, ...] = Field(
        default_factory=tuple, max_length=32
    )
    notes: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def _capabilities_must_be_unique(self) -> ProjectCapabilityManifestV1:
        seen = [item.capability for item in self.capabilities]
        duplicated = sorted({str(item.value) for item in seen if seen.count(item) > 1})
        if duplicated:
            raise ValueError(f"capability declarada em duplicidade: {duplicated}")
        return self

    @model_validator(mode="after")
    def _markers_must_be_normalized(self) -> ProjectCapabilityManifestV1:
        for marker in self.protected_resource_markers:
            if not marker.strip() or marker != marker.strip().lower():
                raise ValueError(
                    "protected_resource_markers devem ser minusculos e sem espacos nas bordas"
                )
        return self

    def declares(self, capability: ProjectCapability) -> bool:
        """O consumidor declarou esta capacidade?"""
        return any(item.capability is capability for item in self.capabilities)

    def has_trait(self, trait: ProducerTrait) -> bool:
        """O consumidor declarou esta propriedade operacional?"""
        return trait in self.traits

    def supports_contract(
        self, capability: ProjectCapability, contract_version: str
    ) -> bool:
        """A capacidade declarada cobre esta versao de contrato?

        Uma capability sem `contract_versions` cobre qualquer versao suportada
        daquele fluxo: e o caso de consumidores que usam o assistente e nao
        submetem payload versionado proprio.
        """
        for item in self.capabilities:
            if item.capability is not capability:
                continue
            if not item.contract_versions:
                return True
            return contract_version in item.contract_versions
        return False
