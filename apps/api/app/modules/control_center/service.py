"""E3 — Control Center: visao administrativa e operacional do PedroCore.

O que ele e
-----------

Uma AGREGACAO somente-leitura do que cada camada ja sabe: projetos e
capabilities declaradas, saude, roteamento, politicas, datasets, avaliacoes,
modelos, risco, outbox e SLO.

O que ele nao e
---------------

Nao e um painel com botoes destrutivos. Nao ha aqui nenhuma acao que apague,
promova, aprove ou reprocesse. A prioridade declarada da frente e
observabilidade e operacao — e um painel que pudesse mutar estado precisaria
de uma superficie de autorizacao propria, que seria uma segunda porta para
decisoes que ja tem porta.

Por que a agregacao vive no servidor
------------------------------------

Se o front juntasse dez chamadas para montar a tela, a regra de "o que conta
como saudavel" acabaria escrita em TypeScript, longe dos testes que a
sustentam. Aqui a resposta e montada uma vez, do lado que responde por ela.

Sanitizacao
-----------

Nenhum campo agregado carrega prompt, payload ou credencial. O painel mostra
CONTAGEM e ESTADO; o detalhe continua atras das rotas que ja o expunham com a
autorizacao delas.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CONTROL_CENTER_VERSION = "control-center-v1"


class ProjectOverview(BaseModel):
    """Um consumidor registrado, pelo que ele DECLARA."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    display_name: str
    capabilities: list[str] = Field(default_factory=list)
    traits: list[str] = Field(default_factory=list)


class RegistryOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    models_total: int = 0
    models_promoted: int = 0
    models_by_status: dict[str, int] = Field(default_factory=dict)
    assets_total: int = 0
    assets_active: int = 0


class RiskOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persistence_mode: str
    persistence_enabled: bool
    contract_signing_configured: bool


class ResilienceOverview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outbox_mode: str
    outbox_durable: bool


class ControlCenterSnapshot(BaseModel):
    """A tela inteira, montada de uma vez, somente leitura."""

    model_config = ConfigDict(extra="forbid")

    control_center_version: Literal["control-center-v1"] = CONTROL_CENTER_VERSION
    generated_at: datetime

    projects: list[ProjectOverview] = Field(default_factory=list)
    registries: RegistryOverview = Field(default_factory=RegistryOverview)
    risk: RiskOverview
    resilience: ResilienceOverview
    health_state: str
    health_degraded: list[str] = Field(default_factory=list)
    health_unavailable: list[str] = Field(default_factory=list)
    health_unknown: list[str] = Field(default_factory=list)
    evaluations_total: int = 0
    shadow_comparisons_total: int = 0

    # Declarado no proprio payload: quem consome esta resposta nao pode
    # concluir que ela permite agir.
    read_only: Literal[True] = True
    contains_sensitive_data: Literal[False] = False


class ControlCenterService:
    """Monta o retrato. Nao muta nada, por construcao."""

    def snapshot(self, now: datetime | None = None) -> ControlCenterSnapshot:
        return ControlCenterSnapshot(
            generated_at=now or datetime.now(timezone.utc),
            projects=self._projects(),
            registries=self._registries(),
            risk=self._risk(),
            resilience=self._resilience(),
            **self._health(),
            evaluations_total=self._evaluations_total(),
            shadow_comparisons_total=self._shadow_total(),
        )

    # --- fontes -----------------------------------------------------------

    @staticmethod
    def _projects() -> list[ProjectOverview]:
        from app.modules.project_context.manifests import PROJECT_MANIFESTS

        return [
            ProjectOverview(
                project_id=project_id,
                display_name=manifest.display_name,
                capabilities=sorted(
                    item.capability.value for item in manifest.capabilities
                ),
                traits=sorted(item.value for item in manifest.traits),
            )
            for project_id, manifest in sorted(PROJECT_MANIFESTS.items())
        ]

    @staticmethod
    def _registries() -> RegistryOverview:
        from app.modules.asset_registry.schemas import AssetStatus
        from app.modules.asset_registry.service import asset_registry_service
        from app.modules.model_registry.service import model_registry_service

        modelos = model_registry_service.list()
        por_estado: dict[str, int] = {}
        for item in modelos:
            por_estado[item.status.value] = por_estado.get(item.status.value, 0) + 1

        assets = asset_registry_service.list_assets()
        ativas = sum(
            1
            for registro in assets
            for versao in registro.versions
            if versao.status is AssetStatus.ACTIVE
        )
        return RegistryOverview(
            models_total=len(modelos),
            models_promoted=len(model_registry_service.promoted()),
            models_by_status=por_estado,
            assets_total=len(assets),
            assets_active=ativas,
        )

    @staticmethod
    def _risk() -> RiskOverview:
        import os

        from app.modules.risk_engine.execution_contract_service import (
            FLAG_CONTRACT_SIGNING_KEY,
        )
        from app.modules.risk_engine.persistence_service import risk_persistence_service
        from app.modules.risk_engine.repository import FLAG_RISK_PERSISTENCE

        chave = (os.environ.get(FLAG_CONTRACT_SIGNING_KEY) or "").strip()
        return RiskOverview(
            persistence_mode=(os.environ.get(FLAG_RISK_PERSISTENCE) or "off").strip()
            or "off",
            persistence_enabled=risk_persistence_service.enabled(),
            # Presenca e comprimento, jamais o valor. Um painel que mostrasse
            # a chave seria um painel que vaza a chave.
            contract_signing_configured=len(chave) >= 32,
        )

    @staticmethod
    def _resilience() -> ResilienceOverview:
        from app.modules.resilience.factory import (
            outbox_is_durable,
            outbox_persistence_mode,
        )

        return ResilienceOverview(
            outbox_mode=outbox_persistence_mode(),
            outbox_durable=outbox_is_durable(),
        )

    @staticmethod
    def _health() -> dict:
        from app.modules.slo.service import slo_service

        instantaneo = slo_service.snapshot()
        return {
            "health_state": instantaneo.state.value,
            "health_degraded": instantaneo.degraded,
            "health_unavailable": instantaneo.unavailable,
            "health_unknown": instantaneo.unknown,
        }

    @staticmethod
    def _evaluations_total() -> int:
        from app.modules.evaluation_plane.service import evaluation_plane_service

        return len(evaluation_plane_service._records)  # noqa: SLF001

    @staticmethod
    def _shadow_total() -> int:
        from app.modules.shadow_execution.service import shadow_execution_service

        return len(shadow_execution_service.comparisons())


control_center_service = ControlCenterService()
