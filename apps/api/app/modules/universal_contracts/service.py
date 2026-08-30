"""Validacao dos Universal Contracts V1.

Ordem da validacao, e por que ela importa
-----------------------------------------

  1. versao do envelope
  2. fronteira de autoridade
  3. forma do payload (Pydantic)
  4. vinculo de identidade (projeto e produtor)
  5. capability declarada no manifesto

A ordem nao e arbitraria. A fronteira de autoridade vem ANTES da validacao de
forma porque um payload que tenta decidir elegibilidade deve ser recusado por
tentar, e nao por estar malformado — a mensagem de erro precisa dizer a verdade
sobre o motivo. Se a forma fosse checada primeiro, um payload que erra o tipo
de um campo E tenta escalar autoridade seria reportado apenas como erro de
tipo, e o integrador corrigiria o tipo sem nunca saber que a escalada era o
problema real.

Fail-closed em toda etapa: nao ha caminho em que uma verificacao ausente,
ambigua ou impossivel resulte em aceitacao.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.modules.universal_contracts.authority import (
    AuthorityViolation,
    scan_for_reserved_authority,
)
from app.modules.universal_contracts.capability_manifest import (
    ProjectCapability,
    ProjectCapabilityManifestV1,
)
from app.modules.universal_contracts.envelope import (
    IntegrationPayloadType,
    PedroCoreIntegrationEnvelopeV1,
    contract_version_for,
)
from app.modules.universal_contracts.versioning import (
    INTEGRATION_ENVELOPE_V1,
    ContractVersionStatus,
    deprecation_warning,
    version_status,
)

# Codigos de recusa. Estaveis por contrato: um integrador programa contra eles.
CONTRACT_VERSION_UNKNOWN = "CONTRACT_VERSION_UNKNOWN"
CONTRACT_PAYLOAD_INVALID = "CONTRACT_PAYLOAD_INVALID"
CONTRACT_AUTHORITY_VIOLATION = "CONTRACT_AUTHORITY_VIOLATION"
CONTRACT_PROJECT_BINDING_MISMATCH = "CONTRACT_PROJECT_BINDING_MISMATCH"
CONTRACT_PRODUCER_BINDING_MISMATCH = "CONTRACT_PRODUCER_BINDING_MISMATCH"
CONTRACT_CAPABILITY_NOT_DECLARED = "CONTRACT_CAPABILITY_NOT_DECLARED"
CONTRACT_CAPABILITY_VERSION_UNSUPPORTED = "CONTRACT_CAPABILITY_VERSION_UNSUPPORTED"
CONTRACT_MANIFEST_MISSING = "CONTRACT_MANIFEST_MISSING"

_CAPABILITY_BY_PAYLOAD_TYPE: dict[IntegrationPayloadType, ProjectCapability] = {
    IntegrationPayloadType.QUALITY_EVIDENCE: ProjectCapability.QUALITY_EVIDENCE,
    IntegrationPayloadType.EXECUTION_OUTCOME: ProjectCapability.EXECUTION_OUTCOME,
    IntegrationPayloadType.LEARNING_SOURCE: ProjectCapability.LEARNING_SOURCE,
}


class ContractValidationResult(BaseModel):
    """Resultado da validacao.

    `accepted` significa apenas "o contrato e valido e a autoridade foi
    respeitada". Nao significa elegibilidade, autorizacao nem promocao: essas
    decisoes continuam no Learning Plane, depois e a parte.
    """

    model_config = ConfigDict(extra="forbid")

    accepted: bool
    error_code: str | None = None
    reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    authority_violations: list[AuthorityViolation] = Field(default_factory=list)
    envelope: PedroCoreIntegrationEnvelopeV1 | None = None
    # Reafirmado no resultado para que nenhum caminho de consumo possa
    # interpretar aceitacao de contrato como promocao a candidato.
    training_candidate_created: bool = False
    automatic_collection_performed: bool = False


def _rejected(
    error_code: str,
    reason: str,
    *,
    violations: list[AuthorityViolation] | None = None,
    warnings: list[str] | None = None,
) -> ContractValidationResult:
    return ContractValidationResult(
        accepted=False,
        error_code=error_code,
        reason=reason,
        warnings=warnings or [],
        authority_violations=violations or [],
    )


class UniversalContractService:
    """Porta de entrada unica dos contratos universais."""

    def validate_envelope(
        self,
        # `object`, e nao `dict`: o envelope chega de fora e a checagem de
        # forma faz parte da validacao, nao uma precondicao ja garantida.
        raw_envelope: object,
        *,
        authenticated_project_id: str,
        authenticated_producer_id: str,
        manifest: ProjectCapabilityManifestV1 | None,
    ) -> ContractValidationResult:
        """Valida um envelope contra identidade real e manifesto declarado.

        `authenticated_project_id` e `authenticated_producer_id` vem da
        credencial resolvida server-side, nunca do payload. O envelope declara
        os mesmos campos apenas para serem CONFERIDOS.
        """
        warnings: list[str] = []

        if not isinstance(raw_envelope, dict):
            return _rejected(
                CONTRACT_PAYLOAD_INVALID, "Envelope deve ser um objeto JSON."
            )

        # 1. Versao do envelope, antes de qualquer interpretacao de conteudo.
        declared_version = str(raw_envelope.get("envelope_version") or INTEGRATION_ENVELOPE_V1)
        status = version_status(declared_version)
        if status is ContractVersionStatus.UNKNOWN:
            return _rejected(
                CONTRACT_VERSION_UNKNOWN,
                f"Versao de envelope desconhecida: '{declared_version}'.",
            )
        if declared_version != INTEGRATION_ENVELOPE_V1:
            return _rejected(
                CONTRACT_VERSION_UNKNOWN,
                f"'{declared_version}' nao e um envelope de integracao.",
            )
        envelope_deprecation = deprecation_warning(declared_version)
        if envelope_deprecation:
            warnings.append(envelope_deprecation)

        # 2. Autoridade antes da forma: recusar por tentar, nao por errar tipo.
        violations = scan_for_reserved_authority(raw_envelope)
        if violations:
            return _rejected(
                CONTRACT_AUTHORITY_VIOLATION,
                (
                    "Payload tenta emitir julgamento reservado ao PedroCore: "
                    + ", ".join(sorted(item.path for item in violations))
                ),
                violations=violations,
                warnings=warnings,
            )

        # 3. Forma.
        try:
            envelope = PedroCoreIntegrationEnvelopeV1.model_validate(raw_envelope)
        except ValidationError as error:
            return _rejected(
                CONTRACT_PAYLOAD_INVALID,
                _summarize_validation_error(error),
                warnings=warnings,
            )

        # 4. Vinculo de identidade. O payload declara; a credencial decide.
        if envelope.project_id.strip().lower() != authenticated_project_id.strip().lower():
            return _rejected(
                CONTRACT_PROJECT_BINDING_MISMATCH,
                "project_id do envelope diverge do projeto da credencial autenticada.",
                warnings=warnings,
            )
        if envelope.producer_id.strip().lower() != authenticated_producer_id.strip().lower():
            return _rejected(
                CONTRACT_PRODUCER_BINDING_MISMATCH,
                "producer_id do envelope diverge do produtor da credencial autenticada.",
                warnings=warnings,
            )

        # 5. Capability declarada no manifesto.
        if manifest is None:
            return _rejected(
                CONTRACT_MANIFEST_MISSING,
                "Projeto sem Capability Manifest registrado; submissao recusada.",
                warnings=warnings,
            )
        required = _CAPABILITY_BY_PAYLOAD_TYPE[envelope.payload_type]
        if not manifest.declares(required):
            return _rejected(
                CONTRACT_CAPABILITY_NOT_DECLARED,
                (
                    f"Projeto nao declara a capability '{required.value}' "
                    "exigida por este payload."
                ),
                warnings=warnings,
            )
        expected_contract = contract_version_for(envelope.payload_type)
        if not manifest.supports_contract(required, expected_contract):
            return _rejected(
                CONTRACT_CAPABILITY_VERSION_UNSUPPORTED,
                (
                    f"Manifesto nao declara suporte a '{expected_contract}' "
                    f"para a capability '{required.value}'."
                ),
                warnings=warnings,
            )
        payload_deprecation = deprecation_warning(expected_contract)
        if payload_deprecation:
            warnings.append(payload_deprecation)

        return ContractValidationResult(
            accepted=True,
            warnings=warnings,
            envelope=envelope,
        )


def _summarize_validation_error(error: ValidationError) -> str:
    """Resumo sanitizado: diz ONDE e O QUE, nunca o valor rejeitado.

    Ecoar o valor devolveria ao log — e a quem le a resposta — exatamente o dado
    que o contrato acabou de recusar por ser inadequado.
    """
    parts: list[str] = []
    for item in error.errors()[:8]:
        location = ".".join(str(piece) for piece in item.get("loc", ()))
        message = str(item.get("msg", "invalido"))
        parts.append(f"{location or 'payload'}: {message}")
    return "Payload invalido — " + "; ".join(parts)


universal_contract_service = UniversalContractService()
