"""Registro de Project Capability Manifests.

Por que os nomes de projeto vivem AQUI e nao no core
----------------------------------------------------

A Era 1 encontrou o motor decidindo por nome: `project_id == "elyra"` dentro da
orquestracao, `project_id == "finguard"` dentro do prompt builder. A regra da
Era 3 nao e "nome de projeto e proibido no repositorio" — seria impossivel, o
Veltrix precisa saber quem sao seus consumidores. A regra e que o nome pode
aparecer no REGISTRO e nunca no MOTOR.

Este arquivo e o registro. Ele e uma tabela de dados, revisavel de uma vez,
onde adicionar um consumidor e adicionar uma linha. O motor, do outro lado,
pergunta `manifest.has_trait(...)` e `manifest.declares(...)` e nunca sabe com
quem esta falando.

A diferenca pratica: antes, habilitar deduplicacao idempotente para um novo
consumidor exigia editar `orchestration/service.py` — 2.900 linhas, coracao do
Runtime Plane. Agora exige acrescentar um trait a uma linha desta tabela.

O que o manifesto nao concede
-----------------------------

Nada de autorizacao de treino, nada de provider real, nada de ampliacao de
`allowed_tasks` alem do que ja esta declarado. O manifesto DESCREVE capacidade;
a matriz de autorizacao e o Learning Plane continuam decidindo permissao.
"""

from __future__ import annotations

from types import MappingProxyType

from app.modules.universal_contracts.capability_manifest import (
    CapabilityDeclaration,
    ProducerTrait,
    ProjectCapabilityManifestV1,
    ProjectCapability,
)
from app.modules.universal_contracts.versioning import (
    EXECUTION_OUTCOME_V1,
    LEARNING_SOURCE_V1,
    QUALITY_EVIDENCE_V1,
)


def _declare(
    capability: ProjectCapability, *versions: str
) -> CapabilityDeclaration:
    return CapabilityDeclaration(capability=capability, contract_versions=tuple(versions))


# O Veltrix como consumidor de si mesmo. Nao e externo e nao tem recurso
# protegido contra si proprio.
_PEDROCORE_MANIFEST = ProjectCapabilityManifestV1(
    project_id="pedrocore",
    display_name="Veltrix",
    producer_id="pedrocore",
    capabilities=(
        _declare(ProjectCapability.ASSISTANT),
        _declare(ProjectCapability.QUALITY_EVIDENCE, QUALITY_EVIDENCE_V1),
        _declare(ProjectCapability.EXECUTION_OUTCOME, EXECUTION_OUTCOME_V1),
        _declare(ProjectCapability.REPORT_INTELLIGENCE),
        _declare(ProjectCapability.INTERACTION_OUTCOME),
        _declare(ProjectCapability.RISK_ANALYSIS),
        _declare(ProjectCapability.ARTIFACT_REFERENCE),
    ),
    traits=frozenset(),
    notes="Sistema local/default do proprio Veltrix.",
)

# FinGuard: sistema externo cujo repositorio o Veltrix nunca deve alcancar.
# `protected_resource_markers` e o que substitui o `if "finguard" in path` que
# existia no leitor de artefatos e no adaptador Playwright.
_FINGUARD_CAPABILITIES = (
    _declare(ProjectCapability.ASSISTANT),
    _declare(ProjectCapability.QUALITY_EVIDENCE, QUALITY_EVIDENCE_V1),
    _declare(ProjectCapability.ARTIFACT_REFERENCE),
)
_FINGUARD_TRAITS = frozenset({ProducerTrait.EXTERNALLY_OWNED})
_FINGUARD_MARKERS = ("finguard",)

_MANIFESTS: dict[str, ProjectCapabilityManifestV1] = {
    "pedrocore": _PEDROCORE_MANIFEST,
    "finguard": ProjectCapabilityManifestV1(
        project_id="finguard",
        display_name="FinGuard",
        producer_id="finguard",
        capabilities=_FINGUARD_CAPABILITIES,
        traits=_FINGUARD_TRAITS,
        protected_resource_markers=_FINGUARD_MARKERS,
        notes="Projeto externo read-only; QA Automation pertence ao FinGuard.",
    ),
    "finguard-local": ProjectCapabilityManifestV1(
        project_id="finguard-local",
        display_name="FinGuard (ambiente local)",
        producer_id="finguard-local",
        capabilities=_FINGUARD_CAPABILITIES,
        traits=_FINGUARD_TRAITS,
        protected_resource_markers=_FINGUARD_MARKERS,
        notes="Mesma fronteira do FinGuard em ambiente local.",
    ),
    "structa": ProjectCapabilityManifestV1(
        project_id="structa",
        display_name="Structa",
        producer_id="structa",
        capabilities=(_declare(ProjectCapability.REPORT_INTELLIGENCE),),
        traits=frozenset({ProducerTrait.EXTERNALLY_OWNED}),
        notes="Consumer externo read-only de Report Intelligence sintetico.",
    ),
    # Elyra e o unico consumidor que hoje declara `IDEMPOTENT_SUBMISSION`.
    # Esse trait — e nao o nome "elyra" — e o que liga a deduplicacao governada
    # na orquestracao.
    "elyra": ProjectCapabilityManifestV1(
        project_id="elyra",
        display_name="Elyra",
        producer_id="elyra",
        capabilities=(
            _declare(ProjectCapability.ASSISTANT),
            _declare(ProjectCapability.LEARNING_SOURCE, LEARNING_SOURCE_V1),
        ),
        traits=frozenset(
            {
                ProducerTrait.EXTERNALLY_OWNED,
                ProducerTrait.IDEMPOTENT_SUBMISSION,
                ProducerTrait.REQUIRES_CORRELATION,
            }
        ),
        notes=(
            "Plataforma externa read-only; submissao governada de fonte de "
            "aprendizado, sem acesso a banco ou Storage da Elyra."
        ),
    ),
}

PROJECT_MANIFESTS: MappingProxyType[str, ProjectCapabilityManifestV1] = MappingProxyType(
    _MANIFESTS
)


def manifest_for(project_id: str | None) -> ProjectCapabilityManifestV1 | None:
    """Manifesto do projeto, ou `None` quando ele nao esta registrado.

    `None` e resposta legitima e significa "consumidor desconhecido". Quem
    chama decide o que fazer com isso, e a decisao correta e sempre a mais
    restritiva — um projeto sem manifesto nao ganha capacidade por omissao.
    """
    if not project_id:
        return None
    return _MANIFESTS.get(project_id.strip().lower())


def declares_capability(project_id: str | None, capability: ProjectCapability) -> bool:
    """Atalho fail-closed: projeto sem manifesto nao declara nada."""
    manifest = manifest_for(project_id)
    return manifest is not None and manifest.declares(capability)


def has_trait(project_id: str | None, trait: ProducerTrait) -> bool:
    """Atalho fail-closed: projeto sem manifesto nao possui trait algum."""
    manifest = manifest_for(project_id)
    return manifest is not None and manifest.has_trait(trait)


def protected_resource_markers() -> frozenset[str]:
    """Todos os marcadores de recurso protegido, de todos os consumidores.

    Agregado de proposito: o leitor de artefatos e o navegador nao perguntam
    "este caminho pertence ao chamador?", e sim "este caminho pertence a ALGUM
    consumidor registrado?". Um consumidor nunca deve alcancar o recurso de
    outro, e o proprio recurso do chamador tambem permanece fora de alcance —
    o Veltrix recebe artefato por payload, nunca por leitura.
    """
    markers: set[str] = set()
    for manifest in _MANIFESTS.values():
        markers.update(manifest.protected_resource_markers)
    return frozenset(markers)
