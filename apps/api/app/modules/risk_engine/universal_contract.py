"""Contrato universal de submissão de risco (Stage R4, resolve P5).

O problema
----------

O Risk Engine nasceu antes dos Universal Contracts. Ele recebe `RiskRequest`
próprio, enquanto QEC, Execution Outcome e Learning Source já têm versionamento
declarado, fronteira de autoridade e congelamento de schema. Um consumidor
externo que quisesse submeter risco usava um contrato que **não passava pela
verificação de autoridade**.

Por que um contrato próprio, e não um payload do envelope existente
-------------------------------------------------------------------

A opção natural seria acrescentar `risk_request` a `IntegrationPayloadType` e
deixá-lo viajar dentro de `PedroCoreIntegrationEnvelopeV1`. Isso mudaria o
JSON Schema do envelope — e portanto o fingerprint congelado de um contrato V1
publicado.

A política deste projeto trata "valor novo em enum" como mudança aditiva que
*pode* atualizar o fingerprint com justificativa. Mas o envelope é o contrato
mais central dos cinco, e alterá-lo para acomodar um domínio que ainda está
evoluindo trocaria estabilidade permanente por conveniência temporária. Os
cinco fingerprints ficam intactos.

O que se ganha mesmo assim: este contrato **reutiliza a mesma maquinaria** —
registro de versões, fronteira de autoridade, vínculo de identidade e
verificação de capability. Ele é um contrato universal a mais, não um caminho
paralelo com regras próprias.

A regra que ele impõe
---------------------

O consumidor declara **fato**: operação, alvos, ambiente, contexto,
permissões. Ele **não** declara veredito — `gate`, `safe`, `severity`,
`approved`, `risk_level` são recusados pela fronteira de autoridade.

    AI interprets. Policy decides.
    Risk predicts. Execution proves.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

RISK_REQUEST_CONTRACT_V1 = "pedrocore-risk-request/v1"

ShortText = Annotated[str, Field(min_length=1, max_length=128)]


class RiskOperationKind(str, Enum):
    """Natureza da operação que o consumidor pretende executar.

    Espelha o vocabulário que o motor V1 já entende. `UNKNOWN` existe e é
    honesto: quem não sabe classificar declara que não sabe, e o motor trata
    isso como bloqueio — o que é melhor do que adivinhar uma categoria branda.
    """

    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    MIGRATION = "MIGRATION"
    DEPLOY = "DEPLOY"
    CONFIG = "CONFIG"
    UNKNOWN = "UNKNOWN"


class RiskOperationDeclaration(BaseModel):
    """O que se pretende fazer e sobre o quê."""

    model_config = ConfigDict(extra="forbid")

    kind: RiskOperationKind
    targets: tuple[ShortText, ...] = Field(default_factory=tuple, max_length=200)
    expected_changes: tuple[str, ...] = Field(default_factory=tuple, max_length=100)


class RiskContextDeclaration(BaseModel):
    """Contexto declarado pelo consumidor — fatos, não conclusões."""

    model_config = ConfigDict(extra="forbid")

    allowed_scope: tuple[ShortText, ...] = Field(default_factory=tuple, max_length=200)
    forbidden_scope: tuple[ShortText, ...] = Field(default_factory=tuple, max_length=200)
    known_modules: tuple[ShortText, ...] = Field(default_factory=tuple, max_length=100)
    constraints: tuple[str, ...] = Field(default_factory=tuple, max_length=50)
    acceptance_criteria: tuple[str, ...] = Field(default_factory=tuple, max_length=50)
    required_tests: tuple[str, ...] = Field(default_factory=tuple, max_length=50)
    external_integrations: tuple[ShortText, ...] = Field(
        default_factory=tuple, max_length=50
    )
    database: str | None = Field(default=None, max_length=128)
    user_scope: str | None = Field(default=None, max_length=128)

    # Fato observável: existe plano de rollback? Nao e uma promessa de que ele
    # funciona — e uma declaracao verificavel na execucao.
    rollback_plan_present: bool = False


class RiskRequestContractV1(BaseModel):
    """Submissão universal de análise de risco.

    Ausência de campo é parte do contrato: não existem `gate`, `severity`,
    `risk_level`, `safe`, `approved` nem `override`. O consumidor traz o fato;
    o veredito é do PedroCore.
    """

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["pedrocore-risk-request/v1"] = RISK_REQUEST_CONTRACT_V1

    request_id: ShortText
    environment: ShortText
    agent_id: ShortText
    request_text: str = Field(..., min_length=1, max_length=8000)
    permissions: tuple[ShortText, ...] = Field(default_factory=tuple, max_length=100)
    requested_operation: RiskOperationDeclaration
    context: RiskContextDeclaration = Field(default_factory=RiskContextDeclaration)

    # Reafirmado no contrato: submeter analise nao executa nada e nao aprova
    # nada. Quem le apenas este objeto nao pode concluir o contrario.
    target_operation_executed: Literal[False] = False
    gate_decided_by_consumer: Literal[False] = False

    def to_risk_request_payload(self, *, producer: str, project_id: str) -> dict:
        """Adapta para o `RiskRequest` V1 que o motor já entende.

        `producer` e `project_id` vêm da credencial autenticada, não do
        payload: é o mesmo princípio dos demais contratos universais — o
        consumidor declara, a credencial decide.

        O motor não muda. Este contrato é uma porta nova para a mesma sala.
        """
        return {
            "request_id": self.request_id,
            "producer": producer,
            "project_id": project_id,
            "request_text": self.request_text,
            "environment": self.environment,
            "agent_id": self.agent_id,
            "permissions": list(self.permissions),
            "requested_operation": {
                "kind": self.requested_operation.kind.value,
                "targets": list(self.requested_operation.targets),
                "expected_changes": list(self.requested_operation.expected_changes),
            },
            "context": {
                "allowed_scope": list(self.context.allowed_scope),
                "forbidden_scope": list(self.context.forbidden_scope),
                "known_modules": list(self.context.known_modules),
                "constraints": list(self.context.constraints),
                "acceptance_criteria": list(self.context.acceptance_criteria),
                "required_tests": list(self.context.required_tests),
                "external_integrations": list(self.context.external_integrations),
                "database": self.context.database,
                "user_scope": self.context.user_scope,
                "rollback_plan_present": self.context.rollback_plan_present,
            },
        }


# ---------------------------------------------------------------------------
# Validacao — reutiliza a maquinaria compartilhada, nao a reimplementa
# ---------------------------------------------------------------------------

RISK_CONTRACT_VERSION_UNKNOWN = "RISK_CONTRACT_VERSION_UNKNOWN"
RISK_CONTRACT_AUTHORITY_VIOLATION = "RISK_CONTRACT_AUTHORITY_VIOLATION"
RISK_CONTRACT_PAYLOAD_INVALID = "RISK_CONTRACT_PAYLOAD_INVALID"
RISK_CONTRACT_CAPABILITY_NOT_DECLARED = "RISK_CONTRACT_CAPABILITY_NOT_DECLARED"
RISK_CONTRACT_MANIFEST_MISSING = "RISK_CONTRACT_MANIFEST_MISSING"


class RiskContractValidation(BaseModel):
    """Resultado da validacao do contrato de risco.

    `accepted` significa apenas que o contrato e valido e a autoridade foi
    respeitada. NAO significa gate, aprovacao nem severidade: quem decide isso
    e o motor, depois, com a analise inteira.
    """

    model_config = ConfigDict(extra="forbid")

    accepted: bool
    error_code: str | None = None
    reason: str | None = None
    contract: RiskRequestContractV1 | None = None
    authority_violations: list[str] = Field(default_factory=list)
    gate_decided: Literal[False] = False


def validate_risk_contract(
    raw_payload: object,
    *,
    authenticated_project_id: str,
    authenticated_producer_id: str,
) -> RiskContractValidation:
    """Valida uma submissao universal de risco.

    Ordem deliberada, a mesma dos demais contratos universais: versao,
    autoridade, forma, capability. A autoridade vem ANTES da forma porque um
    payload que tenta declarar o proprio gate deve ser recusado por TENTAR, e
    nao por errar um tipo — senao o integrador corrige o tipo e nunca descobre
    qual era o problema.
    """
    from pydantic import ValidationError

    from app.modules.project_context.manifests import manifest_for
    from app.modules.universal_contracts.authority import scan_for_reserved_authority
    from app.modules.universal_contracts.capability_manifest import ProjectCapability
    from app.modules.universal_contracts.versioning import (
        ContractVersionStatus,
        version_status,
    )

    if not isinstance(raw_payload, dict):
        return RiskContractValidation(
            accepted=False,
            error_code=RISK_CONTRACT_PAYLOAD_INVALID,
            reason="Contrato de risco deve ser um objeto JSON.",
        )

    declared = str(raw_payload.get("contract_version") or RISK_REQUEST_CONTRACT_V1)
    if (
        version_status(declared) is ContractVersionStatus.UNKNOWN
        or declared != RISK_REQUEST_CONTRACT_V1
    ):
        return RiskContractValidation(
            accepted=False,
            error_code=RISK_CONTRACT_VERSION_UNKNOWN,
            reason=f"Versao de contrato de risco desconhecida: '{declared}'.",
        )

    violations = scan_for_reserved_authority(raw_payload)
    if violations:
        return RiskContractValidation(
            accepted=False,
            error_code=RISK_CONTRACT_AUTHORITY_VIOLATION,
            reason=(
                "Contrato tenta decidir o que pertence ao PedroCore: "
                + ", ".join(sorted(item.path for item in violations))
            ),
            authority_violations=sorted(item.path for item in violations),
        )

    try:
        contract = RiskRequestContractV1.model_validate(raw_payload)
    except ValidationError as error:
        # Resumo sanitizado: diz ONDE e O QUE, nunca o valor recusado.
        parts = [
            f"{'.'.join(str(p) for p in item.get('loc', ())) or 'payload'}: "
            f"{item.get('msg', 'invalido')}"
            for item in error.errors()[:8]
        ]
        return RiskContractValidation(
            accepted=False,
            error_code=RISK_CONTRACT_PAYLOAD_INVALID,
            reason="Payload invalido — " + "; ".join(parts),
        )

    manifest = manifest_for(authenticated_project_id)
    if manifest is None:
        return RiskContractValidation(
            accepted=False,
            error_code=RISK_CONTRACT_MANIFEST_MISSING,
            reason="Projeto sem Capability Manifest registrado.",
        )
    if not manifest.declares(ProjectCapability.RISK_ANALYSIS):
        return RiskContractValidation(
            accepted=False,
            error_code=RISK_CONTRACT_CAPABILITY_NOT_DECLARED,
            reason="Projeto nao declara a capability 'risk_analysis'.",
        )

    return RiskContractValidation(accepted=True, contract=contract)
