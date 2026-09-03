"""Declaracao das fronteiras internas do Veltrix.

ADR-PEDROCORE-CONTROL-PLANE-01.

Por que este modulo existe
--------------------------

O Veltrix acumulou duas responsabilidades de natureza diferente: responder
agora (Runtime Plane) e aprender depois (Learning Plane). As duas existem e as
duas funcionam. O que faltava era a FRONTEIRA — nada no codigo dizia a que
plano um modulo pertence, e nada impedia que a dependencia apontasse para o
lado errado.

Uma fronteira que vive so em Markdown apodrece. A auditoria da Era 1 encontrou
um documento de arquitetura listando 8 endpoints quando o codigo expoe 37.
Por isso a fronteira aqui e DADO, lido por teste, e nao prosa: um modulo novo
sem plano declarado quebra o build, e um import na direcao errada tambem.

O Veltrix continua sendo um modular monolith: um processo, um `pyproject`,
um `app.main`. A separacao e logica e verificada, nao fisica e distribuida.
Nenhum arquivo foi movido para produzir estas fronteiras — mudanca fisica so
se justifica quando melhora dependencia, clareza, manutencao ou teste, e
renomear pastas nao melhora nenhuma das quatro.

Direcao da dependencia
----------------------

::

    Runtime Plane  ──── structured operational sources ────►  Learning Plane

O Learning Plane PODE consumir contratos e evidencias produzidos pelo Runtime
Plane: e assim que ele aprende. O Runtime Plane NAO deve depender do Learning
Plane, porque responder a uma pergunta normal do Assistant nao pode exigir que
a maquinaria de treinamento esteja de pe.

As excecoes existentes estao em `RUNTIME_TO_LEARNING_EXCEPTIONS`, uma a uma,
com justificativa. Uma excecao enumerada e auditavel; uma excecao implicita
nao e.
"""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType


class Plane(str, Enum):
    """Agrupamento logico ao qual um modulo pertence.

    `SHARED_KERNEL` e `CONSUMER_CAPABILITY` nao sao planos no sentido da ADR:
    sao agrupamentos de apoio, declarados explicitamente porque fingir que nao
    existem seria pior do que nomea-los.
    """

    RUNTIME = "runtime_plane"
    LEARNING = "learning_plane"
    SHARED_KERNEL = "shared_kernel"
    CONSUMER_CAPABILITY = "consumer_capability"


# ---------------------------------------------------------------------------
# Runtime Plane — responder agora.
#
# Sincrono, sensivel a latencia, indisponibilidade imediatamente visivel.
# ---------------------------------------------------------------------------
_RUNTIME_MODULES = frozenset(
    {
        # Orchestration
        "orchestration",
        "task_router",
        "policy_enforcement",
        "prompt_builder",
        "output_budget",
        # Providers
        "providers",
        "provider_authorization",
        "provider_binding",
        "provider_catalog",
        "provider_health",
        "shadow_routing",
        # Assistant
        "chat",
        "artifacts",
        "artifact_reader",
        # Retrieval
        "retrieval",
        # Operational Memory
        "operational_memory",
        # Report Intelligence
        "report_intelligence",
        "report_memory",
        # Interaction Outcomes
        "interaction_outcomes",
        # Risk Engine e Execution Contracts (mesmo modulo, `risk_engine`)
        "risk_engine",
        # Risk Console: CLI e TUI sobre o Risk Engine. E Runtime, e nao
        # Consumer Capability, porque nao pertence a nenhum consumidor —
        # atende qualquer projeto que declare `risk_analysis`. Nao decide
        # risco: consome os mesmos servicos que o router HTTP consome.
        "risk_console",
        # --- Platform Evolution -------------------------------------------
        #
        # Todas Runtime: decidem, roteiam, medem ou registram o que o runtime
        # faz. Nenhuma promove candidato a treino, e nenhuma pertence a um
        # consumidor especifico.
        #
        # `evaluation_plane` merece nota: ele avalia SUJEITOS do runtime
        # (provider, modelo, prompt, rota) e produz evidencia. Nao promove e
        # nao governa aprendizado — isso continua no Learning Plane.
        "policy_engine",
        "correlation",
        "compatibility",
        "consumer_sdk",
        "model_registry",
        "asset_registry",
        "evaluation_plane",
        "shadow_execution",
        "routing_intelligence",
        "slo",
        "control_center",
        "disaster_recovery",
        # Durabilidade das registries de plataforma. Runtime: guarda o
        # estado que o runtime produz, e nao governa aprendizado.
        "platform_persistence",
        # Risk Intake: resolve contexto antes da analise. Runtime, e nao
        # Consumer Capability — atende qualquer projeto que declare
        # superficie, e nao pertence a consumidor nenhum.
        "risk_intake",
        # Safe Reuse
        "safe_reuse",
        # QA e avaliacao operacional do runtime
        "qa_analysis",
        "qa_response",
        "visual_qa",
        "evaluation",
        "eval_harness",
        "intelligence_layer",
        # Capacidades operacionais opt-in
        "exploration",
        "ocr",
        # Evidence Platform (Era 4). Runtime Plane, e nao Learning Plane: ela
        # RECEBE e registra fato operacional sincronamente, e nao promove nada.
        # Se estivesse no Learning Plane, ingerir evidencia exigiria a
        # maquinaria de treinamento de pe — o oposto do invariante.
        "evidence_platform",
        # Resiliencia de integracao (Era 6): outbox de referencia e
        # reconciliacao. Runtime Plane — existe para que o Assistant e a
        # ingestao continuem uteis quando a rede falha.
        "resilience",
        # Auditoria e observabilidade do runtime.
        #
        # Poderiam parecer infraestrutura transversal, mas nao sao: `audit`
        # conhece `provider_binding` e `observability` conhece `orchestration`,
        # `providers` e `evaluation`. Elas auditam e observam a EXECUCAO, que e
        # um assunto do Runtime Plane. Declara-las no Shared Kernel foi a
        # primeira tentativa desta ADR, e o teste de fronteira a reprovou.
        "audit",
        "observability",
    }
)

# ---------------------------------------------------------------------------
# Learning Plane — aprender depois.
#
# Assincrono por natureza, insensivel a latencia. Sua indisponibilidade deve
# ser invisivel para quem so quer uma resposta.
#
# Hoje o Learning Plane inteiro vive em UM modulo. Isso nao e acidente nem
# defeito: Dataset Foundation, eligibility, privacy, provenance, authorization,
# lifecycle e readiness sao uma unica politica coesa, versionada em conjunto
# (`training-acquisition-v1`, `dataset-foundation-v1`, `dataset-readiness-v2`).
# Fatiar em pastas o que compartilha versao de politica criaria fronteira falsa.
# ---------------------------------------------------------------------------
_LEARNING_MODULES = frozenset(
    {
        "training_data",
        # Dataset Control Plane (Era 7). Learning Plane porque o Dataset
        # Ownership e do Veltrix: definir escopo, versionar, registrar
        # linhagem e decidir split sao decisoes de aprendizado, nao de runtime.
        "dataset_registry",
        # Evaluation & Training Foundation (Era 8). Learning Plane: decide o
        # que treinar, com qual dataset e sob qual politica. Quem roda a GPU e
        # um `TrainingBackend` — nenhum nome de provider entra no dominio.
        "training_foundation",
    }
)

# ---------------------------------------------------------------------------
# Shared Kernel — consumido pelos dois planos, pertence a nenhum.
#
# Identidade, codigos de contrato e contexto de projeto sao infraestrutura
# transversal. Coloca-los em um dos planos obrigaria o outro a atravessar a
# fronteira para usar o basico.
#
# O criterio nao e "parece generico", e "nao depende de nenhum plano". Modulos
# que pareciam kernel mas conheciam provider e orquestracao foram movidos para
# o Runtime Plane quando o teste de fronteira os reprovou.
# ---------------------------------------------------------------------------
_SHARED_KERNEL_MODULES = frozenset(
    {
        "caller_identity",
        "contracts",
        "project_context",
        "real_features",
        "docs_graph",
        # Universal Contracts V1 (ADR-PEDROCORE-UNIVERSAL-CONTRACTS-01).
        #
        # Kernel por construcao, e nao por conveniencia: o modulo e formado por
        # schemas Pydantic puros e NAO importa nenhum plano. E essa ausencia de
        # dependencia que permite ao Runtime Plane e ao Learning Plane falarem a
        # mesma lingua sem que um precise conhecer o outro. Traduzir um contrato
        # para objeto de dominio e responsabilidade do plano que o consome.
        "universal_contracts",
    }
)

# ---------------------------------------------------------------------------
# Consumer Capabilities — adaptadores de contrato por consumidor externo.
#
# Esta e a fronteira onde regra especifica de projeto e LEGITIMA, precisamente
# para que ela nao fique no core generico. Um modulo aqui pode conhecer o nome
# do seu consumidor; um modulo do Runtime Plane nao deveria.
# ---------------------------------------------------------------------------
_CONSUMER_CAPABILITY_MODULES = frozenset(
    {
        "elyra_textual",
        "elyra_multimodal",
        "elyra_learning",
    }
)

MODULE_PLANES: MappingProxyType[str, Plane] = MappingProxyType(
    {
        **{name: Plane.RUNTIME for name in _RUNTIME_MODULES},
        **{name: Plane.LEARNING for name in _LEARNING_MODULES},
        **{name: Plane.SHARED_KERNEL for name in _SHARED_KERNEL_MODULES},
        **{name: Plane.CONSUMER_CAPABILITY for name in _CONSUMER_CAPABILITY_MODULES},
    }
)


# ---------------------------------------------------------------------------
# Excecoes nominais a direcao da dependencia.
#
# Formato: (modulo do Runtime Plane, modulo do Learning Plane) -> justificativa.
#
# Adicionar uma entrada aqui e uma decisao de arquitetura, nao uma conveniencia
# de implementacao. A lista e curta de proposito: quando ela crescer a ponto de
# nao caber em uma tela, a regra virou decoracao.
# ---------------------------------------------------------------------------
RUNTIME_TO_LEARNING_EXCEPTIONS: MappingProxyType[tuple[str, str], str] = MappingProxyType(
    {
        ("orchestration", "training_data"): (
            "A submissao e a revogacao governadas de candidato chegam pelo mesmo "
            "endpoint `/api/orchestrate` que o Assistant, entao a orquestracao "
            "precisa despachar para o Learning Plane. O acoplamento e estreito "
            "(apenas `_elyra_learning_outcome`, que nunca toca provider) e o "
            "import da maquinaria pesada e TARDIO, dentro da funcao, para que "
            "uma falha do Learning Plane nao impeca o Runtime Plane de carregar."
        ),
    }
)


def plane_of(module_name: str) -> Plane | None:
    """Plano declarado do modulo, ou `None` se ele nao foi declarado."""
    return MODULE_PLANES.get(module_name)


def modules_in(plane: Plane) -> frozenset[str]:
    """Modulos declarados no agrupamento informado."""
    return frozenset(name for name, value in MODULE_PLANES.items() if value is plane)


def is_declared_exception(runtime_module: str, learning_module: str) -> bool:
    """A aresta Runtime -> Learning informada esta declarada e justificada?"""
    return (runtime_module, learning_module) in RUNTIME_TO_LEARNING_EXCEPTIONS
