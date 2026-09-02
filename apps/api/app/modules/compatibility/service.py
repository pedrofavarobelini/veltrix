"""Servico da matriz: calcula a resposta a partir do que cada camada declara.

Nenhuma tabela de projetos mora aqui. Cada dimensao e resolvida perguntando a
fonte que ja e dona dela — manifesto, registro de versoes, catalogo de
provider — e a matriz apenas compoe.
"""

from __future__ import annotations

from app.modules.compatibility.schemas import (
    CompatibilityAnswer,
    CompatibilityDimension,
    CompatibilityFinding,
    CompatibilityQuery,
    CompatibilityStatus,
    worst,
)

# --- codigos de motivo ----------------------------------------------------

PROJECT_NOT_REGISTERED = "PROJECT_NOT_REGISTERED"
CAPABILITY_NOT_DECLARED = "CAPABILITY_NOT_DECLARED"
CAPABILITY_UNKNOWN = "CAPABILITY_UNKNOWN"
CONTRACT_VERSION_UNKNOWN = "CONTRACT_VERSION_UNKNOWN"
CONTRACT_VERSION_DEPRECATED = "CONTRACT_VERSION_DEPRECATED"
SDK_VERSION_UNSUPPORTED = "SDK_VERSION_UNSUPPORTED"
RISK_VERSION_UNSUPPORTED = "RISK_VERSION_UNSUPPORTED"
POLICY_VERSION_UNSUPPORTED = "POLICY_VERSION_UNSUPPORTED"
PROVIDER_MODEL_UNKNOWN = "PROVIDER_MODEL_UNKNOWN"
ASSET_VERSION_UNKNOWN = "ASSET_VERSION_UNKNOWN"
COMBINATION_SUPPORTED = "COMBINATION_SUPPORTED"


class CompatibilityService:
    """Compoe o veredito. Nao guarda estado por projeto."""

    def check(self, query: CompatibilityQuery) -> CompatibilityAnswer:
        findings: list[CompatibilityFinding] = []
        findings.append(self._project(query))
        findings.append(self._capability(query))
        findings.extend(self._contracts(query))
        if query.sdk_version:
            findings.append(self._sdk(query.sdk_version))
        if query.risk_version:
            findings.append(self._risk(query.risk_version))
        if query.policy_version:
            findings.append(self._policy(query.policy_version))
        if query.provider_model:
            findings.append(self._provider_model(query.provider_model))
        findings.extend(self._assets(query))

        status = worst([item.status for item in findings])
        return CompatibilityAnswer(
            project_id=query.project_id.strip().lower(),
            capability=query.capability.strip().lower(),
            status=status,
            findings=findings,
            blocking=[
                item.reason_code
                for item in findings
                if item.status is CompatibilityStatus.INCOMPATIBLE
            ],
            warnings=[
                item.reason_code
                for item in findings
                if item.status
                in {CompatibilityStatus.DEPRECATED, CompatibilityStatus.UNKNOWN}
            ],
        )

    # --- dimensoes --------------------------------------------------------

    @staticmethod
    def _project(query: CompatibilityQuery) -> CompatibilityFinding:
        from app.modules.project_context.manifests import manifest_for

        manifest = manifest_for(query.project_id)
        if manifest is None:
            return CompatibilityFinding(
                dimension=CompatibilityDimension.PROJECT,
                subject=query.project_id,
                status=CompatibilityStatus.INCOMPATIBLE,
                reason_code=PROJECT_NOT_REGISTERED,
                explanation="Projeto sem Capability Manifest registrado.",
            )
        return CompatibilityFinding(
            dimension=CompatibilityDimension.PROJECT,
            subject=query.project_id,
            status=CompatibilityStatus.SUPPORTED,
            reason_code=COMBINATION_SUPPORTED,
            explanation="Projeto registrado com manifesto válido.",
        )

    @staticmethod
    def _capability(query: CompatibilityQuery) -> CompatibilityFinding:
        from app.modules.project_context.manifests import manifest_for
        from app.modules.universal_contracts.capability_manifest import ProjectCapability

        try:
            capability = ProjectCapability(query.capability.strip().lower())
        except ValueError:
            # Capability que o core nao conhece e UNKNOWN, nao INCOMPATIBLE:
            # pode ser um consumidor a frente do servidor, e isso se descobre,
            # nao se decreta.
            return CompatibilityFinding(
                dimension=CompatibilityDimension.CAPABILITY,
                subject=query.capability,
                status=CompatibilityStatus.UNKNOWN,
                reason_code=CAPABILITY_UNKNOWN,
                explanation="Capability não reconhecida por esta versão do core.",
            )

        manifest = manifest_for(query.project_id)
        if manifest is None or not manifest.declares(capability):
            return CompatibilityFinding(
                dimension=CompatibilityDimension.CAPABILITY,
                subject=query.capability,
                status=CompatibilityStatus.INCOMPATIBLE,
                reason_code=CAPABILITY_NOT_DECLARED,
                explanation="O projeto não declara esta capability no manifesto.",
            )
        return CompatibilityFinding(
            dimension=CompatibilityDimension.CAPABILITY,
            subject=query.capability,
            status=CompatibilityStatus.SUPPORTED,
            reason_code=COMBINATION_SUPPORTED,
            explanation="Capability declarada pelo projeto.",
        )

    @staticmethod
    def _contracts(query: CompatibilityQuery) -> list[CompatibilityFinding]:
        from app.modules.universal_contracts.versioning import (
            ContractVersionStatus,
            version_status,
        )

        achados: list[CompatibilityFinding] = []
        for versao in query.contract_versions:
            estado = version_status(versao)
            if estado is ContractVersionStatus.UNKNOWN:
                achados.append(
                    CompatibilityFinding(
                        dimension=CompatibilityDimension.CONTRACT_VERSION,
                        subject=versao,
                        status=CompatibilityStatus.INCOMPATIBLE,
                        reason_code=CONTRACT_VERSION_UNKNOWN,
                        explanation="Versão de contrato desconhecida pelo servidor.",
                    )
                )
            elif estado is ContractVersionStatus.DEPRECATED:
                achados.append(
                    CompatibilityFinding(
                        dimension=CompatibilityDimension.CONTRACT_VERSION,
                        subject=versao,
                        status=CompatibilityStatus.DEPRECATED,
                        reason_code=CONTRACT_VERSION_DEPRECATED,
                        explanation="Versão ainda aceita, porém marcada como obsoleta.",
                    )
                )
            else:
                achados.append(
                    CompatibilityFinding(
                        dimension=CompatibilityDimension.CONTRACT_VERSION,
                        subject=versao,
                        status=CompatibilityStatus.SUPPORTED,
                        reason_code=COMBINATION_SUPPORTED,
                        explanation="Versão de contrato suportada.",
                    )
                )
        return achados

    @staticmethod
    def _sdk(version: str) -> CompatibilityFinding:
        from app.modules.consumer_sdk.version import SDK_SUPPORTED_VERSIONS

        suportada = version.strip() in SDK_SUPPORTED_VERSIONS
        return CompatibilityFinding(
            dimension=CompatibilityDimension.SDK_VERSION,
            subject=version,
            status=CompatibilityStatus.SUPPORTED
            if suportada
            else CompatibilityStatus.INCOMPATIBLE,
            reason_code=COMBINATION_SUPPORTED if suportada else SDK_VERSION_UNSUPPORTED,
            explanation=(
                "Versão do SDK suportada."
                if suportada
                else "Versão do SDK não reconhecida por este servidor."
            ),
        )

    @staticmethod
    def _risk(version: str) -> CompatibilityFinding:
        from app.modules.risk_engine.pre_execution_schemas import (
            PRE_EXECUTION_RISK_POLICY_VERSION,
        )

        suportada = version.strip() == PRE_EXECUTION_RISK_POLICY_VERSION
        return CompatibilityFinding(
            dimension=CompatibilityDimension.RISK_VERSION,
            subject=version,
            status=CompatibilityStatus.SUPPORTED
            if suportada
            else CompatibilityStatus.INCOMPATIBLE,
            reason_code=COMBINATION_SUPPORTED if suportada else RISK_VERSION_UNSUPPORTED,
            explanation=(
                "Versão da política de risco suportada."
                if suportada
                else "Versão da política de risco não corresponde à do servidor."
            ),
        )

    @staticmethod
    def _policy(version: str) -> CompatibilityFinding:
        from app.modules.policy_engine.schemas import POLICY_ENGINE_VERSION

        suportada = version.strip() == POLICY_ENGINE_VERSION
        return CompatibilityFinding(
            dimension=CompatibilityDimension.POLICY_VERSION,
            subject=version,
            status=CompatibilityStatus.SUPPORTED
            if suportada
            else CompatibilityStatus.INCOMPATIBLE,
            reason_code=COMBINATION_SUPPORTED
            if suportada
            else POLICY_VERSION_UNSUPPORTED,
            explanation=(
                "Versão do Policy Engine suportada."
                if suportada
                else "Versão do Policy Engine não corresponde à do servidor."
            ),
        )

    @staticmethod
    def _provider_model(subject: str) -> CompatibilityFinding:
        from app.modules.model_registry.service import model_registry_service

        entrada = model_registry_service.find(subject)
        if entrada is None:
            return CompatibilityFinding(
                dimension=CompatibilityDimension.PROVIDER_MODEL,
                subject=subject,
                status=CompatibilityStatus.UNKNOWN,
                reason_code=PROVIDER_MODEL_UNKNOWN,
                explanation="Modelo não registrado no Model Registry.",
            )
        from app.modules.model_registry.schemas import ModelStatus

        usavel = entrada.status in {ModelStatus.PROMOTED, ModelStatus.APPROVED}
        return CompatibilityFinding(
            dimension=CompatibilityDimension.PROVIDER_MODEL,
            subject=subject,
            status=CompatibilityStatus.SUPPORTED
            if usavel
            else CompatibilityStatus.INCOMPATIBLE,
            reason_code=COMBINATION_SUPPORTED if usavel else PROVIDER_MODEL_UNKNOWN,
            explanation=(
                f"Modelo em estado {entrada.status.value}."
                if usavel
                else f"Modelo em estado {entrada.status.value}, não liberado para uso."
            ),
        )

    @staticmethod
    def _assets(query: CompatibilityQuery) -> list[CompatibilityFinding]:
        from app.modules.asset_registry.service import asset_registry_service

        achados: list[CompatibilityFinding] = []
        for referencia in query.asset_versions:
            ativo = asset_registry_service.active_for(referencia)
            achados.append(
                CompatibilityFinding(
                    dimension=CompatibilityDimension.ASSET_VERSION,
                    subject=referencia,
                    status=CompatibilityStatus.SUPPORTED
                    if ativo is not None
                    else CompatibilityStatus.UNKNOWN,
                    reason_code=COMBINATION_SUPPORTED
                    if ativo is not None
                    else ASSET_VERSION_UNKNOWN,
                    explanation=(
                        "Asset governado e ativo."
                        if ativo is not None
                        else "Asset não encontrado como ativo no registry."
                    ),
                )
            )
        return achados


compatibility_service = CompatibilityService()
