import asyncio
import os
import time
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.modules.artifact_reader.service import artifact_reader_service
from app.modules.artifacts.schemas import ArtifactInput, ArtifactProcessingResult
from app.modules.artifacts.service import PATH_LIKE_METADATA_KEYS, artifact_service
from app.modules.audit.service import audit_service
from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    OriginClaimResult,
)
from app.modules.caller_identity.service import caller_identity_service
from app.modules.chat.schemas import ChatRequest
from app.modules.contracts import codes
from app.modules.contracts.codes import WarningItem, make_warning
from app.modules.evaluation.service import evaluation_service
from app.modules.elyra_textual.idempotency import elyra_idempotency_service
from app.modules.elyra_textual.schemas import ELYRA_TASK_TYPE, ElyraTextualInputV1
from app.modules.elyra_textual.service import (
    IDEMPOTENCY_CONFLICT_REASON,
    INTERNAL_FAILURE_REASON,
    PROVIDER_MISMATCH_REASON,
    elyra_textual_service,
)
from app.modules.elyra_multimodal.schemas import (
    ELYRA_MULTIMODAL_TASK_TYPE,
    ElyraMultimodalInputV1,
)
from app.modules.elyra_multimodal.service import (
    IDEMPOTENCY_CONFLICT_REASON as MULTIMODAL_IDEMPOTENCY_CONFLICT_REASON,
)
from app.modules.elyra_multimodal.service import (
    INTERNAL_FAILURE_REASON as MULTIMODAL_INTERNAL_FAILURE_REASON,
)
from app.modules.elyra_multimodal.service import (
    PROVIDER_MISMATCH_REASON as MULTIMODAL_PROVIDER_MISMATCH_REASON,
)
from app.modules.elyra_multimodal.service import elyra_multimodal_service
from app.modules.elyra_learning.schemas import (
    ELYRA_LEARNING_TASK_TYPE,
    REVOKE_OPERATION,
    SUBMIT_OPERATION,
)
from app.modules.elyra_learning.service import (
    IDEMPOTENCY_CONFLICT_REASON as LEARNING_IDEMPOTENCY_CONFLICT_REASON,
)
from app.modules.elyra_learning.service import (
    INTERNAL_FAILURE_REASON as LEARNING_INTERNAL_FAILURE_REASON,
)
from app.modules.elyra_learning.service import (
    NOT_FOUND_REASON as LEARNING_NOT_FOUND_REASON,
)
from app.modules.elyra_learning.service import elyra_learning_service
# ADR-PEDROCORE-CONTROL-PLANE-01: o Runtime Plane nao carrega a maquinaria do
# Learning Plane na importacao. `training_data.schemas` e contrato puro e pode
# vir no topo; `training_data.acquisition` arrasta Candidate Store, repository e
# driver PostgreSQL, e por isso e importado tardiamente em
# `_elyra_learning_outcome`. Assim uma falha do Learning Plane nao impede o
# Assistant de carregar e responder.
from app.modules.training_data.schemas import TrainingPurpose, TrainingSourceType
from app.modules.universal_contracts.capability_manifest import ProducerTrait
from app.modules.exploration.service import exploration_service
from app.modules.intelligence_layer.service import intelligence_layer_service
from app.modules.observability.service import observability_service
from app.modules.orchestration.schemas import (
    AssistantResponsePayload,
    OrchestrationOutcome,
)
from app.modules.provider_authorization.service import provider_authorization_service
from app.modules.provider_binding.schemas import SelectedProviderModel
from app.modules.provider_binding.service import provider_binding_service
from app.modules.provider_health.schemas import (
    CompletionCertainty,
    FailureClassification,
)
from app.modules.provider_health.service import (
    ProviderCircuitOpenError,
    provider_health_service,
)
from app.modules.output_budget.schemas import OutputBudget
from app.modules.output_budget.service import output_budget_service
from app.modules.provider_catalog.service import provider_catalog_service
from app.modules.providers.base import (
    ProviderConfigError,
    ProviderExecutionError,
    ProviderOutputRejectedError,
    ProviderResponse,
    ProviderTransportTimeoutError,
    TransportClose,
)
from app.modules.providers.local_model_provider import local_model_ready
from app.modules.shadow_routing.schemas import EliminationReason, RoutingMode
from app.modules.shadow_routing.service import shadow_routing_service
from app.modules.report_memory.service import report_memory_service
from app.modules.policy_enforcement.service import policy_enforcement_service
from app.modules.real_features import service as real_features
from app.modules.project_context.manifests import has_trait
from app.modules.project_context.service import (
    EMPTY_ALLOWED_TASKS_WARNING,
    FINGUARD_ORIGIN_SYSTEMS,
    TASK_NOT_ALLOWED_WARNING,
    UNKNOWN_PROJECT_POLICY_WARNING,
    project_context_resolver,
)
from app.modules.visual_qa.service import visual_qa_service
from app.modules.prompt_builder.schemas import PromptBuildInput
from app.modules.prompt_builder.service import prompt_builder
from app.modules.providers.registry import provider_registry
from app.modules.qa_analysis.service import qa_text_analyzer
from app.modules.qa_response.service import (
    QA_NO_ARTIFACTS_WARNING,
    RELEASE_GATE_TASK_TYPE,
    qa_response_service,
)
from app.modules.task_router.service import (
    CRITICAL_TASK_TYPES,
    FALLBACK_CRITICAL_WARNING,
    MOCK_CRITICAL_WARNING,
    task_router,
)

# Pseudo-providers locais: nenhuma chamada externa, resposta determinística.
LOCAL_PROVIDERS = {"local", "local_qa"}
LOCAL_PROVIDER_NAME = "local_qa"
LOCAL_PROVIDER_MODEL = "local-qa-v1"

# Provider generativo local opt-in (PEDROCORE-LOCAL-MODEL-01).
# local_model NÃO é local_qa e nunca aprova release gate.
LOCAL_MODEL_PROVIDER_NAME = "local_model"

FINANCE_ADVICE_TASK_TYPE = "finance_advice"

FINANCIAL_DISCLAIMER_TEXT = (
    "Aviso: esta resposta é informativa e conservadora, não é aconselhamento "
    "financeiro definitivo, não executa nenhuma ação financeira e não altera "
    "dados. Decisões financeiras exigem validação humana."
)

# Tasks de memória de relatório: sempre acompanhadas do aviso de que
# relatórios não treinam IA.
REPORT_MEMORY_TASK_TYPES = {
    "report_ingestion",
    "project_memory_summary",
    "report_memory_query",
}

REPORT_NOT_TRAINING_WARNING = (
    "Relatórios técnicos não treinam IA; alimentam apenas sinais e memória "
    "técnica consultável."
)

LOCAL_MODEL_NOT_AUTHORIZED_WARNING = (
    "local_model exige allow_local_model=true explícito no payload; "
    "fallback seguro aplicado."
)
LOCAL_MODEL_DISABLED_WARNING = (
    "local_model desabilitado (PEDROCORE_ENABLE_LOCAL_MODEL=false ou backend "
    "não configurado); fallback seguro aplicado."
)
LOCAL_MODEL_TASK_BLOCKED_WARNING = (
    "local_model não pode ser usado em release gate ou tarefa crítica; "
    "fallback seguro aplicado."
)

PROVIDER_REAL_BLOCKED_WARNING = (
    "Provider real bloqueado pelo safe mode (allow_real_provider=false); "
    "fallback seguro aplicado."
)
AUTO_PROVIDER_NAME = "auto"
AUTO_REAL_PROVIDER_CANDIDATES = ("gemini",)
AUTO_PROVIDER_REAL_BLOCKED_WARNING = (
    "Provider auto exige allow_real_provider=true explicito; fallback Mock seguro aplicado."
)
PROVIDER_REAL_UNAVAILABLE_WARNING = (
    "Provider real autorizado, mas nenhum provider real configurado esta disponivel; "
    "fallback Mock seguro aplicado."
)
PROVIDER_TIMEOUT_ENV = "PEDROCORE_PROVIDER_TIMEOUT_SECONDS"
PROVIDER_TIMEOUT_WARNING = "Provider excedeu o tempo limite; fallback seguro aplicado."
PROVIDER_COMPLETION_AMBIGUOUS_WARNING = (
    "A espera pelo provider terminou, mas não há prova de que a geração remota "
    "tenha sido interrompida; nenhuma nova tentativa é iniciada."
)
PROVIDER_TRANSPORT_TIMEOUT_WARNING = (
    "O transporte HTTP expirou e foi encerrado localmente; a conclusão remota "
    "permanece desconhecida e nenhuma nova tentativa é iniciada."
)
PROVIDER_OUTPUT_TRUNCATED_WARNING = (
    "Resposta do provider atingiu o orçamento de saída e ficou incompleta; "
    "conteúdo parcial não foi publicado e o fallback seguro foi aplicado."
)
PROVIDER_OUTPUT_REJECTED_WARNING = (
    "Provider encerrou a geração por condição anormal; resposta não utilizável "
    "e fallback seguro aplicado."
)
PROVIDER_CIRCUIT_OPEN_WARNING = (
    "Provider temporariamente bloqueado pelo circuit breaker; fallback seguro aplicado."
)
FLAG_REAL_FALLBACK_ENABLED = "PEDROCORE_REAL_FALLBACK_ENABLED"
MAX_REAL_PROVIDER_ATTEMPTS = 2
REAL_FALLBACK_ALLOWED_TASKS = frozenset(
    {
        "assistant_chat",
        "ecosystem_assistant",
    }
)
REAL_FALLBACK_SAFE_CLASSIFICATIONS = frozenset(
    {FailureClassification.PROVIDER_PRE_DISPATCH.value}
)
REAL_FALLBACK_STARTED_REASON = (
    "Secundário iniciado somente após falha pre-dispatch comprovadamente concluída."
)
REAL_FALLBACK_DISABLED_REASON = "Kill switch interno de fallback real está desligado."
REAL_FALLBACK_TASK_BLOCKED_REASON = (
    "Task fora da allowlist conservadora de fallback real."
)
REAL_FALLBACK_UNSAFE_FAILURE_REASON = (
    "Falha não comprova ausência de chamada externa ativa; secundário bloqueado."
)
REAL_FALLBACK_NO_CANDIDATE_REASON = (
    "Nenhum provider secundário distinto passou novamente por todos os filtros."
)
REAL_FALLBACK_MAX_ATTEMPTS_REASON = (
    "Limite absoluto de duas tentativas de provider atingido; terceiro bloqueado."
)

# MULTI-PROVIDER-SAFE-EVOLUTION Etapa 2: provider real depende de autorização
# explícita por projeto/papel/ambiente. Negar nunca vira chamada real: vira
# fallback Mock seguro.
PROVIDER_NOT_AUTHORIZED_WARNING = (
    "Provider real não autorizado para o projeto autenticado neste ambiente; "
    "fallback Mock seguro aplicado."
)
# Negação por IDENTIDADE (não por falha operacional): credencial compartilhada
# não identifica projeto e nunca alcança provider real.
PROVIDER_AMBIGUOUS_IDENTITY_WARNING = (
    "Credencial compartilhada não identifica o projeto do caller; nenhum "
    "provider real é autorizado e a resposta segura local foi aplicada."
)

# Modos de seleção registrados na auditoria.
SELECTION_MODE_AUTO = "auto"
SELECTION_MODE_EXPLICIT = "explicit"
SELECTION_MODE_LOCAL = "local_deterministic"

# Etapa 3: combinação provider+modelo incoerente é bloqueada antes do adapter.
BINDING_BLOCKED_ANSWER_PREFIX = (
    "Solicitação bloqueada pelo controle de provider e modelo do Veltrix."
)
IDENTITY_BLOCKED_ANSWER_PREFIX = (
    "Solicitação bloqueada pelo controle de identidade do Veltrix."
)

# Respostas seguras e conservadoras usadas por _mock_fallback(). Nunca devem
# conter erro tecnico bruto, nome de classe de provider/exception, nem rotulo
# de debug (ex.: "MockProvider", "mock-v1", "Modelo solicitado", texto de
# arquitetura interna). Detalhes tecnicos ficam apenas em error/error_code/
# warnings/audit, que ja sao retornados separadamente pelo chamador.
#
# A mensagem e escolhida pelo CONTEXTO da requisicao, nao por um texto unico:
# o disclaimer financeiro e correto para o FinGuard e absurdo para "me fale o
# que foi feito recentemente no sistema". Ver _fallback_answers().
SAFE_FALLBACK_ANSWER = (
    "No momento não foi possível obter uma resposta completa do provider "
    "solicitado. Isso não executa nenhuma ação financeira nem altera seus "
    "dados. Tente novamente em instantes ou reformule sua pergunta."
)
NO_MOCK_FALLBACK_ANSWER = (
    "A solicitação não foi concluída pelo provider solicitado e o fallback "
    "local foi desabilitado explicitamente para esta requisição."
)

# Chat geral (interface do proprio Veltrix e demais consumers nao financeiros):
# nenhuma mencao a dinheiro, conta ou dados financeiros.
GENERAL_FALLBACK_ANSWER = (
    "O provider selecionado não concluiu a solicitação e foi utilizado o "
    "fallback local. Tente novamente em instantes ou reformule sua pergunta."
)
GENERAL_NO_MOCK_FALLBACK_ANSWER = (
    "Não foi possível concluir a solicitação com o provider selecionado."
)

READER_FINGUARD_ORIGIN_WARNING = (
    "Artifact Reader não está disponível para origem FinGuard nesta frente; "
    "artefatos devem ser enviados por payload."
)

VISUAL_ONLY_RELEASE_GATE_WARNING = (
    "Release gate não pode ser liberado apenas com evidência visual não analisada; "
    "envie evidência textual."
)


# Cada capability Elyra tem escopo de idempotencia proprio e, por consequencia,
# codigo e razao proprios. Um mapa nomeado evita que uma capability nova herde
# silenciosamente a mensagem de outra — foi assim que o learning quase reportou
# um conflito como se fosse do contrato textual.
_ELYRA_CONFLICT_BY_TASK = {
    ELYRA_TASK_TYPE: (codes.ELYRA_IDEMPOTENCY_CONFLICT, IDEMPOTENCY_CONFLICT_REASON),
    ELYRA_MULTIMODAL_TASK_TYPE: (
        codes.ELYRA_MULTIMODAL_IDEMPOTENCY_CONFLICT,
        MULTIMODAL_IDEMPOTENCY_CONFLICT_REASON,
    ),
    ELYRA_LEARNING_TASK_TYPE: (
        codes.ELYRA_LEARNING_IDEMPOTENCY_CONFLICT,
        LEARNING_IDEMPOTENCY_CONFLICT_REASON,
    ),
}

_ELYRA_FAILURE_BY_TASK = {
    ELYRA_TASK_TYPE: (codes.ELYRA_INTERNAL_FAILURE, INTERNAL_FAILURE_REASON),
    ELYRA_MULTIMODAL_TASK_TYPE: (
        codes.ELYRA_MULTIMODAL_INTERNAL_FAILURE,
        MULTIMODAL_INTERNAL_FAILURE_REASON,
    ),
    ELYRA_LEARNING_TASK_TYPE: (
        codes.ELYRA_LEARNING_INTERNAL_FAILURE,
        LEARNING_INTERNAL_FAILURE_REASON,
    ),
}


class OrchestrationService:
    """Pipeline central: Task Router → Project Context → Policy → Artifacts →
    Provider (com safe mode) → QA Text Analyzer local → QA Response/Release Gate → Audit."""

    async def execute(
        self,
        payload: ChatRequest,
        caller: AuthenticatedCallerContext | None = None,
    ) -> OrchestrationOutcome:
        """Executa o pipeline real e publica somente uma projeção sanitizada no
        ring buffer local quando a observabilidade estiver explicitamente ativa.

        `caller` é a identidade derivada da credencial autenticada pelo router.
        Sem contexto explícito, aplica-se o contexto default (dev/local ou
        fail-closed quando existe registro de callers configurado).
        """
        started = time.perf_counter()
        caller = caller or caller_identity_service.default_context()

        async def execute_once() -> OrchestrationOutcome:
            try:
                if observability_service.force_total_provider_failure(payload):
                    raise RuntimeError(
                        "QA_TOTAL_PROVIDER_FAILURE: providers e fallback indisponíveis "
                        "no cenário controlado."
                    )
                return await self._execute_pipeline(payload, caller)
            except Exception as exc:
                observability_service.record_exception(
                    payload, exc, (time.perf_counter() - started) * 1_000
                )
                normalized_task = (payload.task_type or "").strip().lower()
                if normalized_task == ELYRA_TASK_TYPE:
                    return self._elyra_contract_blocked_outcome(
                        payload=payload,
                        caller=caller,
                        error_code=codes.ELYRA_INTERNAL_FAILURE,
                        reason=INTERNAL_FAILURE_REASON,
                        started=started,
                        provider_used="unknown",
                    )
                if normalized_task == ELYRA_MULTIMODAL_TASK_TYPE:
                    return self._elyra_contract_blocked_outcome(
                        payload=payload,
                        caller=caller,
                        error_code=codes.ELYRA_MULTIMODAL_INTERNAL_FAILURE,
                        reason=MULTIMODAL_INTERNAL_FAILURE_REASON,
                        started=started,
                        provider_used="unknown",
                    )
                if normalized_task == ELYRA_LEARNING_TASK_TYPE:
                    return self._elyra_contract_blocked_outcome(
                        payload=payload,
                        caller=caller,
                        error_code=codes.ELYRA_LEARNING_INTERNAL_FAILURE,
                        reason=LEARNING_INTERNAL_FAILURE_REASON,
                        started=started,
                        provider_used="none",
                    )
                raise

        normalized_task = (payload.task_type or "").strip().lower()
        is_elyra = normalized_task in {
            ELYRA_TASK_TYPE,
            ELYRA_MULTIMODAL_TASK_TYPE,
            ELYRA_LEARNING_TASK_TYPE,
        }
        # ADR-PEDROCORE-UNIVERSAL-CONTRACTS-01: a deduplicacao governada passou
        # a depender do trait declarado `IDEMPOTENT_SUBMISSION`, e nao do nome do
        # consumidor. Habilitar um consumidor novo virou uma linha no registro de
        # manifests, sem tocar neste modulo.
        can_deduplicate = bool(
            is_elyra
            and payload.idempotency_key
            and payload.correlation_id
            and has_trait(caller.project_id, ProducerTrait.IDEMPOTENT_SUBMISSION)
        )
        if can_deduplicate:
            execution = await elyra_idempotency_service.execute(
                scope=f"elyra:{caller.project_id}:{normalized_task}",
                idempotency_key=payload.idempotency_key or "",
                fingerprint=elyra_idempotency_service.request_fingerprint(payload),
                operation=execute_once,
            )
            if execution.conflict:
                conflict_code, conflict_reason = _ELYRA_CONFLICT_BY_TASK[
                    normalized_task
                ]
                outcome = self._elyra_contract_blocked_outcome(
                    payload=payload,
                    caller=caller,
                    error_code=conflict_code,
                    reason=conflict_reason,
                    started=started,
                )
            else:
                if execution.value is None:
                    failure_code, failure_reason = _ELYRA_FAILURE_BY_TASK[
                        normalized_task
                    ]
                    outcome = self._elyra_contract_blocked_outcome(
                        payload=payload,
                        caller=caller,
                        error_code=failure_code,
                        reason=failure_reason,
                        started=started,
                        provider_used="unknown",
                    )
                else:
                    outcome = execution.value
                if execution.replayed and execution.value is not None:
                    outcome.idempotency_replayed = True
                    outcome.audit.idempotency_replayed = True
        else:
            outcome = await execute_once()

        observability_service.record_orchestration(
            payload, outcome, (time.perf_counter() - started) * 1_000
        )
        return outcome

    async def _execute_pipeline(
        self,
        payload: ChatRequest,
        caller: AuthenticatedCallerContext | None = None,
    ) -> OrchestrationOutcome:
        started = time.perf_counter()

        strategy = task_router.resolve(payload.task_type)
        caller = caller or caller_identity_service.default_context()

        # Identidade primeiro: a origem declarada no payload é apenas alegação.
        declared_project = project_context_resolver.resolve(payload.origin_system)
        origin_claim = caller_identity_service.validate_origin_claim(
            caller, payload.origin_system, declared_project.project_id
        )
        requested_provider = (payload.provider or settings.default_provider).lower()

        if origin_claim.rejected:
            return self._identity_blocked_outcome(
                payload=payload,
                strategy=strategy,
                project=declared_project,
                caller=caller,
                origin_claim=origin_claim,
                requested_provider=requested_provider,
                error_code=codes.CALLER_ORIGIN_MISMATCH,
                reason=origin_claim.reason or codes.CALLER_ORIGIN_MISMATCH,
                started=started,
            )

        # Project Context (policy/tasks) vem da alegação validada; a IDENTIDADE
        # usada para autorizar provider real vem de origin_claim.identity_project_id,
        # que uma credencial ambígua nunca consegue definir.
        project = project_context_resolver.resolve(origin_claim.context_project_id)
        policy = project_context_resolver.evaluate_task_policy(project, strategy.task_type)

        restriction = caller_identity_service.evaluate_request_restrictions(
            caller, requested_provider, payload.model
        )
        if restriction.blocked:
            return self._identity_blocked_outcome(
                payload=payload,
                strategy=strategy,
                project=project,
                caller=caller,
                origin_claim=origin_claim,
                requested_provider=requested_provider,
                error_code=restriction.error_code or codes.CALLER_PROVIDER_SELECTION_NOT_ALLOWED,
                reason=restriction.reason or "Requisição não permitida para o papel do caller.",
                started=started,
            )

        enforcement = policy_enforcement_service.evaluate(
            raw_task_type=payload.task_type,
            strategy=strategy,
            project=project,
            policy=policy,
            metadata=payload.metadata,
            context=payload.context,
            enforce=real_features.enforce_project_policy(),
        )
        if enforcement.blocked:
            return self._policy_blocked_outcome(
                payload=payload,
                strategy=strategy,
                project=project,
                policy=policy,
                enforcement=enforcement,
                requested_provider=requested_provider,
                caller=caller,
                origin_claim=origin_claim,
                started=started,
            )

        elyra_request: ElyraTextualInputV1 | None = None
        if strategy.task_type == ELYRA_TASK_TYPE:
            elyra_validation = elyra_textual_service.validate_input(payload, caller)
            if not elyra_validation.valid:
                return self._elyra_contract_blocked_outcome(
                    payload=payload,
                    caller=caller,
                    error_code=(
                        elyra_validation.error_code
                        or codes.ELYRA_INPUT_SCHEMA_INVALID
                    ),
                    reason=elyra_validation.reason or "Contrato Elyra inválido.",
                    started=started,
                )
            elyra_request = elyra_validation.value

        # Stage 12: capability multimodal propria. Um payload textual jamais
        # satisfaz este contrato e vice-versa; as duas validacoes sao exclusivas.
        multimodal_request: ElyraMultimodalInputV1 | None = None
        if strategy.task_type == ELYRA_MULTIMODAL_TASK_TYPE:
            multimodal_validation = elyra_multimodal_service.validate_input(
                payload, caller
            )
            if not multimodal_validation.valid:
                return self._elyra_contract_blocked_outcome(
                    payload=payload,
                    caller=caller,
                    error_code=(
                        multimodal_validation.error_code
                        or codes.ELYRA_MULTIMODAL_INPUT_SCHEMA_INVALID
                    ),
                    reason=(
                        multimodal_validation.reason
                        or "Contrato multimodal Elyra inválido."
                    ),
                    started=started,
                )
            multimodal_request = multimodal_validation.value

        # Stage 13: learning governado. E uma operacao de GOVERNANCA, nao de
        # geracao: nenhum provider e consultado, nenhum prompt e construido e
        # nenhum modelo e treinado. Por isso o caminho termina aqui, antes do
        # dispatch, em vez de atravessar o pipeline de provider com um no-op.
        if strategy.task_type == ELYRA_LEARNING_TASK_TYPE:
            return self._elyra_learning_outcome(
                payload=payload,
                caller=caller,
                strategy=strategy,
                project=project,
                policy=policy,
                origin_claim=origin_claim,
                started=started,
            )

        # PEDROCORE-MODEL-FOUNDATION-01: plano determinístico da Intelligence
        # Layer, calculado após policy e antes do Prompt Builder. Nesta frente
        # o plano é apenas metadado interno do outcome; não altera prompt,
        # resposta, warnings nem contratos públicos.
        intelligence_plan = intelligence_layer_service.build_plan(
            strategy=strategy, project=project
        )

        # ECOSYSTEM-INTELLIGENCE-SUITE-01: memória técnica opcional por request.
        # Default context_from_memory=false; snapshot limitado/sanitizado,
        # nunca leitura de arquivo ou repositório externo.
        memory_used = False
        memory_block: str | None = None
        memory_items: list[WarningItem] = []
        if payload.context_from_memory:
            memory_block, memory_items = report_memory_service.context_block(
                project.project_id
            )
            memory_used = memory_block is not None

        selection_mode = self._selection_mode(requested_provider)

        # Etapas 4/5: um único avaliador puro calcula a mesma política em
        # shadow e enforced. Somente o pipeline lê a decisão em enforced.
        routing_decision = shadow_routing_service.evaluate(
            caller=caller,
            identity_project_id=origin_claim.identity_project_id,
            context_project_id=project.project_id,
            task_type=strategy.task_type,
            allow_real_provider=payload.allow_real_provider,
            policy_allowed=policy.allowed,
        )
        enforced_auto = (
            selection_mode == SELECTION_MODE_AUTO
            and routing_decision.routing_mode is RoutingMode.ENFORCED
        )
        auto_candidate = (
            routing_decision.selected_provider
            if enforced_auto
            else self._auto_candidate()
        )

        # Etapa 3: provider e modelo são validados como unidade ANTES de
        # qualquer adapter. Em enforced o binding usa exatamente o candidato
        # produzido pelo motor único.
        binding = provider_binding_service.resolve(
            requested_provider=requested_provider,
            requested_model=payload.model,
            selection_mode=selection_mode,
            caller_role=caller.caller_role,
            task_type=strategy.task_type,
            auto_candidate=auto_candidate,
        )
        auto_binding_invalid = (
            selection_mode == SELECTION_MODE_AUTO
            and binding.requested_model is None
            and binding.invalid
        )
        requested_adapter = provider_registry.get(requested_provider)
        safe_mode_preempts_default_binding = (
            selection_mode == SELECTION_MODE_EXPLICIT
            and payload.model is None
            and not payload.allow_real_provider
            and requested_adapter is not None
            and requested_adapter.real_provider
        )
        if (
            binding.invalid
            and not auto_binding_invalid
            and not safe_mode_preempts_default_binding
        ):
            return self._identity_blocked_outcome(
                payload=payload,
                strategy=strategy,
                project=project,
                caller=caller,
                origin_claim=origin_claim,
                requested_provider=requested_provider,
                error_code=binding.error_code or codes.PROVIDER_MODEL_BINDING_INVALID,
                reason=binding.reason or "Combinação provider/modelo inválida.",
                started=started,
                answer_prefix=BINDING_BLOCKED_ANSWER_PREFIX,
                binding=binding,
            )

        shadow_decision = routing_decision

        effective_artifacts, reader_items = self._apply_artifact_reader(payload)
        artifacts_result = artifact_service.process(effective_artifacts)

        audit = audit_service.create(
            origin_system=payload.origin_system,
            task_type=strategy.task_type,
            provider_requested=requested_provider,
            criticality=strategy.criticality,
            caller=caller,
            origin_claim=origin_claim,
            provider_selection_mode=selection_mode,
            binding=binding,
            correlation_id=payload.correlation_id,
            idempotency_key=payload.idempotency_key,
        )
        audit.real_fallback_enabled = self._real_fallback_enabled()

        prompt = prompt_builder.build(
            PromptBuildInput(
                message=payload.message,
                mode=payload.mode,
                system_prompt=(
                    elyra_textual_service.system_prompt()
                    if elyra_request is not None
                    else elyra_multimodal_service.system_prompt()
                    if multimodal_request is not None
                    else payload.system_prompt
                ),
                strategy=strategy,
                project=project,
                origin_system=payload.origin_system,
                context=payload.context,
                metadata=payload.metadata,
                artifacts_text_block=artifacts_result.text_block,
                intelligence_instructions=intelligence_plan.instructions,
                memory_block=memory_block,
            )
        )

        fallback_used = False
        safe_mode_blocked = False
        error: str | None = None
        error_code: str | None = None
        local_model_items: list[WarningItem] = []
        provider_items: list[WarningItem] = []
        if binding.warning_code:
            provider_items.append(
                make_warning(binding.warning_code, binding.warning_reason or "")
            )
        if auto_binding_invalid:
            provider_items.append(
                make_warning(
                    binding.error_code or codes.PROVIDER_MODEL_BINDING_INVALID,
                    binding.reason or "Binding default inválido para provider=auto.",
                )
            )

        if elyra_request is not None and requested_provider == "mock":
            mock_output = elyra_textual_service.deterministic_mock(
                elyra_request,
                payload.correlation_id or "",
            )
            answer = elyra_textual_service.serialize_output(mock_output)
            provider_used = "mock"
            model_used = "mock-v1"
            analysis = None
        elif multimodal_request is not None and requested_provider == "mock":
            multimodal_mock = elyra_multimodal_service.deterministic_mock(
                multimodal_request,
                payload.correlation_id or "",
            )
            answer = elyra_multimodal_service.serialize_output(multimodal_mock)
            provider_used = "mock"
            model_used = "mock-v1"
            analysis = None
        elif requested_provider in LOCAL_PROVIDERS:
            analysis = qa_text_analyzer.analyze(
                task_type=strategy.task_type,
                artifacts_result=artifacts_result,
                fallback_used=False,
                safe_mode_blocked=False,
            )
            if analysis is not None:
                answer = analysis.summary
            else:
                answer = (
                    "Processamento local determinístico concluído; "
                    "nenhuma análise QA aplicável a esta task."
                )
            provider_used = LOCAL_PROVIDER_NAME
            model_used = LOCAL_PROVIDER_MODEL
        else:
            provider = provider_registry.get(requested_provider)

            if requested_provider == AUTO_PROVIDER_NAME:
                if auto_binding_invalid:
                    error = binding.reason or "Binding default inválido para provider=auto."
                    error_code = (
                        binding.error_code or codes.PROVIDER_MODEL_BINDING_INVALID
                    )
                    (
                        answer,
                        provider_used,
                        model_used,
                        fallback_used,
                    ) = await self._mock_fallback(
                        payload, requested_provider, error, prompt.enriched_system_prompt
                    )
                elif not payload.allow_real_provider:
                    safe_mode_blocked = True
                    error = AUTO_PROVIDER_REAL_BLOCKED_WARNING
                    error_code = codes.PROVIDER_REAL_BLOCKED
                    (
                        answer,
                        provider_used,
                        model_used,
                        fallback_used,
                    ) = await self._mock_fallback(
                        payload, requested_provider, error, prompt.enriched_system_prompt
                    )
                else:
                    if enforced_auto:
                        provider, denial = self._select_enforced_real_provider(
                            routing_decision,
                            caller=caller,
                            project_id=origin_claim.identity_project_id,
                        )
                    else:
                        provider, denial = self._select_auto_real_provider(
                            caller=caller, project_id=origin_claim.identity_project_id
                        )
                    if provider is None:
                        if denial is not None:
                            audit.authorization_result = denial.result.value
                            audit.authorization_reason_code = denial.error_code
                            error = self._denial_message(denial)
                            error_code = (
                                denial.error_code or codes.PROVIDER_NOT_AUTHORIZED_FOR_PROJECT
                            )
                        elif enforced_auto:
                            error_code, error = self._routing_unavailable(
                                routing_decision
                            )
                        else:
                            error = PROVIDER_REAL_UNAVAILABLE_WARNING
                            error_code = codes.PROVIDER_REAL_UNAVAILABLE
                        provider_items.append(make_warning(error_code, error))
                        (
                            answer,
                            provider_used,
                            model_used,
                            fallback_used,
                        ) = await self._mock_fallback(
                            payload, requested_provider, error, prompt.enriched_system_prompt
                        )
                    else:
                        audit.provider_selected = provider.name
                        audit.authorization_result = "allowed"
                        try:
                            result = await self._generate_real_attempt(
                                provider,
                                payload,
                                prompt.enriched_system_prompt,
                                binding.model_id,
                                audit=audit,
                                environment=caller.environment,
                                ordinal=1,
                                selection_reason=routing_decision.selection_reason,
                                fallback_candidate=enforced_auto,
                                task_type=strategy.task_type,
                            )
                            answer = result.answer
                            provider_used = result.provider
                            model_used = result.model
                        except Exception as exc:
                            error, signal_code, signal_items = (
                                self._provider_failure_signal(exc)
                            )
                            if signal_code is not None:
                                error_code = signal_code
                            provider_items.extend(signal_items)
                            secondary_result = None
                            if enforced_auto:
                                try:
                                    secondary_result = (
                                        await self._try_enforced_real_fallback(
                                            primary_provider=provider,
                                            payload=payload,
                                            enriched_system_prompt=(
                                                prompt.enriched_system_prompt
                                            ),
                                            caller=caller,
                                            identity_project_id=(
                                                origin_claim.identity_project_id
                                            ),
                                            context_project_id=project.project_id,
                                            task_type=strategy.task_type,
                                            policy_allowed=policy.allowed,
                                            audit=audit,
                                        )
                                    )
                                except Exception:
                                    audit.real_fallback_reason = (
                                        "Falha interna ao avaliar o secundário; "
                                        "Mock seguro aplicado."
                                    )
                                    if audit.provider_attempts:
                                        audit.provider_attempts[-1][
                                            "fallback_eligible"
                                        ] = False
                                        audit.provider_attempts[-1][
                                            "fallback_decision_reason"
                                        ] = audit.real_fallback_reason
                            if secondary_result is not None:
                                answer = secondary_result.answer
                                provider_used = secondary_result.provider
                                model_used = secondary_result.model
                                audit.provider_selected = secondary_result.provider
                                fallback_used = True
                            else:
                                answer, provider_used, model_used, fallback_used = (
                                    await self._mock_fallback(
                                        payload,
                                        requested_provider,
                                        error,
                                        prompt.enriched_system_prompt,
                                    )
                                )
            elif provider is None:
                error = f"Provider não suportado: {requested_provider}"
                (
                    answer,
                    provider_used,
                    model_used,
                    fallback_used,
                ) = await self._mock_fallback(
                    payload, requested_provider, error, prompt.enriched_system_prompt
                )
            elif requested_provider == LOCAL_MODEL_PROVIDER_NAME:
                (
                    answer,
                    provider_used,
                    model_used,
                    fallback_used,
                    error,
                    error_code,
                    local_model_items,
                ) = await self._execute_local_model(payload, strategy, prompt, binding)
            elif provider.real_provider and not payload.allow_real_provider:
                safe_mode_blocked = True
                error = PROVIDER_REAL_BLOCKED_WARNING
                error_code = codes.PROVIDER_REAL_BLOCKED
                (
                    answer,
                    provider_used,
                    model_used,
                    fallback_used,
                ) = await self._mock_fallback(
                    payload, requested_provider, error, prompt.enriched_system_prompt
                )
            else:
                # Seleção explícita autorizada: consentimento da requisição
                # (allow_real_provider) já passou, mas a matriz de projeto
                # ainda pode negar o provider real.
                denial = None
                if provider.real_provider:
                    decision = provider_authorization_service.evaluate(
                        identity_strength=caller.identity_strength,
                        project_id=origin_claim.identity_project_id,
                        caller_role=caller.caller_role,
                        environment=caller.environment,
                        provider_id=provider.name,
                    )
                    audit.authorization_result = decision.result.value
                    audit.authorization_reason_code = decision.error_code
                    if decision.denied:
                        denial = decision
                    else:
                        audit.provider_selected = provider.name

                if denial is not None:
                    error = self._denial_message(denial)
                    error_code = denial.error_code or codes.PROVIDER_NOT_AUTHORIZED_FOR_PROJECT
                    provider_items.append(make_warning(error_code, error))
                    (
                        answer,
                        provider_used,
                        model_used,
                        fallback_used,
                    ) = await self._mock_fallback(
                        payload, requested_provider, error, prompt.enriched_system_prompt
                    )
                else:
                    try:
                        if provider.real_provider:
                            result = await self._generate_real_attempt(
                                provider,
                                payload,
                                prompt.enriched_system_prompt,
                                binding.model_id,
                                audit=audit,
                                environment=caller.environment,
                                ordinal=1,
                                selection_reason=(
                                    "Provider selecionado explicitamente pelo caller."
                                ),
                                fallback_candidate=False,
                                task_type=strategy.task_type,
                            )
                        else:
                            result = await self._generate_with_timeout(
                                provider,
                                payload,
                                prompt.enriched_system_prompt,
                                binding.model_id,
                                strategy.task_type,
                            )
                        answer = result.answer
                        provider_used = result.provider
                        model_used = result.model
                    except Exception as exc:
                        # Provider não-real sem configuração continua sendo
                        # apenas indisponibilidade silenciosa, como antes.
                        report_config_error = provider.real_provider or not isinstance(
                            exc, ProviderConfigError
                        )
                        error, signal_code, signal_items = (
                            self._provider_failure_signal(exc)
                        )
                        if report_config_error:
                            if signal_code is not None:
                                error_code = signal_code
                            provider_items.extend(signal_items)
                        (
                            answer,
                            provider_used,
                            model_used,
                            fallback_used,
                        ) = await self._mock_fallback(
                            payload, requested_provider, error, prompt.enriched_system_prompt
                        )

            analysis = qa_text_analyzer.analyze(
                task_type=strategy.task_type,
                artifacts_result=artifacts_result,
                fallback_used=fallback_used,
                safe_mode_blocked=safe_mode_blocked,
            )

        elyra_output = None
        elyra_blocked_reason: str | None = None
        if elyra_request is not None:
            expected_provider = binding.provider_id or requested_provider
            expected_model = binding.model_id
            provider_mismatch = bool(
                error is None
                and (
                    provider_used != expected_provider
                    or (expected_model is not None and model_used != expected_model)
                )
            )
            if provider_mismatch:
                error_code = codes.ELYRA_PROVIDER_MISMATCH
                error = PROVIDER_MISMATCH_REASON
                elyra_blocked_reason = error
                provider_items.append(make_warning(error_code, error))
                answer = "Resposta Elyra recusada por divergência de provider/modelo."
            elif error is None and provider_used != "none" and not fallback_used:
                output_validation = elyra_textual_service.validate_output(
                    answer,
                    elyra_request,
                    payload.correlation_id or "",
                )
                if output_validation.valid:
                    elyra_output = output_validation.value
                    answer = elyra_output.summary
                else:
                    error_code = (
                        output_validation.error_code or codes.ELYRA_OUTPUT_INVALID
                    )
                    error = output_validation.reason or "Output Elyra inválido."
                    elyra_blocked_reason = error
                    provider_items.append(make_warning(error_code, error))
                    answer = "Resposta Elyra recusada por incompatibilidade de schema."
            else:
                elyra_blocked_reason = error or (
                    "Fallback não é resultado válido para o contrato textual Elyra."
                )

        multimodal_output = None
        if multimodal_request is not None:
            expected_provider = binding.provider_id or requested_provider
            expected_model = binding.model_id
            provider_mismatch = bool(
                error is None
                and (
                    provider_used != expected_provider
                    or (expected_model is not None and model_used != expected_model)
                )
            )
            if provider_mismatch:
                error_code = codes.ELYRA_MULTIMODAL_PROVIDER_MISMATCH
                error = MULTIMODAL_PROVIDER_MISMATCH_REASON
                elyra_blocked_reason = error
                provider_items.append(make_warning(error_code, error))
                answer = (
                    "Resposta multimodal Elyra recusada por divergência de "
                    "provider/modelo."
                )
            elif error is None and provider_used != "none" and not fallback_used:
                multimodal_validation = elyra_multimodal_service.validate_output(
                    answer,
                    multimodal_request,
                    payload.correlation_id or "",
                )
                if multimodal_validation.valid:
                    multimodal_output = multimodal_validation.value
                    answer = multimodal_output.summary
                else:
                    error_code = (
                        multimodal_validation.error_code
                        or codes.ELYRA_MULTIMODAL_OUTPUT_INVALID
                    )
                    error = (
                        multimodal_validation.reason
                        or "Output multimodal Elyra inválido."
                    )
                    elyra_blocked_reason = error
                    provider_items.append(make_warning(error_code, error))
                    answer = (
                        "Resposta multimodal Elyra recusada por incompatibilidade "
                        "de schema."
                    )
            else:
                elyra_blocked_reason = error or (
                    "Fallback não é resultado válido para o contrato multimodal Elyra."
                )

        # finance_advice é conservador: disclaimer obrigatório na resposta.
        if strategy.task_type == FINANCE_ADVICE_TASK_TYPE:
            answer = f"{answer}\n\n{FINANCIAL_DISCLAIMER_TEXT}"

        qa_skeleton = qa_response_service.build_skeleton(
            task_type=strategy.task_type,
            fallback_used=fallback_used,
            artifacts_result=artifacts_result,
            analysis=analysis,
            safe_mode_blocked=safe_mode_blocked,
        )

        release_gate = None
        if strategy.task_type == RELEASE_GATE_TASK_TYPE:
            release_gate = qa_response_service.evaluate_release_gate(
                artifacts_result=artifacts_result,
                analysis=analysis,
                fallback_used=fallback_used,
                safe_mode_blocked=safe_mode_blocked,
                provider_used=provider_used,
            )
            if qa_skeleton is not None:
                qa_skeleton.can_advance = release_gate.can_advance
                qa_skeleton.blocked_reason = release_gate.blocked_reason
                if not release_gate.can_advance:
                    qa_skeleton.status = "blocked"

        visual_qa = visual_qa_service.analyze(
            artifacts_result, allow_real_provider=payload.allow_real_provider
        )

        exploration = exploration_service.build(
            task_type=strategy.task_type,
            message=payload.message,
            payload_context=payload.context,
            payload_metadata=payload.metadata,
        )

        warning_items = self._collect_warnings(
            strategy=strategy,
            project_warnings=project.warnings,
            policy_warnings=policy.warnings,
            artifacts_result=artifacts_result,
            analysis=analysis,
            release_gate=release_gate,
            provider_used=provider_used,
            fallback_used=fallback_used,
            safe_mode_blocked=safe_mode_blocked,
            reader_items=reader_items,
            visual_qa=visual_qa,
            exploration=exploration,
            memory_items=memory_items,
            local_model_items=local_model_items,
            provider_items=provider_items,
        )

        no_mock_fallback_blocked = (
            not payload.allow_mock_fallback
            and error is not None
            and provider_used == "none"
            and model_used == "none"
        )

        blocked_reason: str | None = None
        if elyra_blocked_reason:
            blocked_reason = elyra_blocked_reason
        elif no_mock_fallback_blocked:
            blocked_reason = error
        elif release_gate is not None and not release_gate.can_advance:
            blocked_reason = release_gate.blocked_reason
        elif artifacts_result.path_rejected:
            blocked_reason = "Artefato com caminho de arquivo rejeitado."
        elif analysis is not None and analysis.risk_level == "critical":
            blocked_reason = "Risco crítico detectado na análise QA local."
        elif safe_mode_blocked and strategy.criticality in {"high", "critical"}:
            blocked_reason = "Provider real bloqueado pelo safe mode em tarefa crítica."

        status = "blocked" if blocked_reason else "ok"

        audit.fallback_used = fallback_used
        audit.provider_used = provider_used
        audit.safe_mode_blocked = safe_mode_blocked
        audit.status = status
        audit.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        audit.risk_level = analysis.risk_level if analysis is not None else None
        audit.can_advance = (
            qa_skeleton.can_advance if qa_skeleton is not None else None
        )

        # Comparação por identificadores, depois da execução real. Em shadow a
        # decisão é só observada; em enforced ela já controlou a escolha.
        shadow_decision = shadow_routing_service.compare_with_actual(
            shadow_decision, actual_provider=provider_used, actual_model=model_used
        )
        audit.routing_mode = shadow_decision.routing_mode.value
        audit.routing_policy_version = shadow_decision.policy_version
        audit.routing_configuration_valid = shadow_decision.configuration_valid
        audit.routing_configuration_reason = shadow_decision.configuration_reason
        audit.routing_selected_provider = shadow_decision.selected_provider
        audit.routing_selected_model = shadow_decision.selected_model
        audit.routing_selection_reason = shadow_decision.selection_reason
        audit.routing_candidates_considered = self._routing_candidates(
            shadow_decision.candidates_considered
        )
        audit.routing_candidates_eliminated = self._routing_candidates(
            shadow_decision.candidates_eliminated
        )
        audit.real_provider_attempt_count = sum(
            1
            for attempt in audit.provider_attempts
            if attempt.get("external_dispatch") is True
        )
        audit.real_provider_attempt_record_count = len(audit.provider_attempts)
        self._apply_generation_audit(audit)

        shadow_active = shadow_decision.routing_mode is RoutingMode.SHADOW
        audit.shadow_enabled = shadow_active
        audit.shadow_selected_provider = (
            shadow_decision.selected_provider if shadow_active else None
        )
        audit.shadow_selected_model = (
            shadow_decision.selected_model if shadow_active else None
        )
        audit.shadow_would_differ = (
            shadow_decision.would_differ_from_actual if shadow_active else None
        )
        audit.shadow_policy_version = (
            shadow_decision.policy_version if shadow_active else None
        )

        return OrchestrationOutcome(
            answer=answer,
            provider_requested=requested_provider,
            provider_used=provider_used,
            model=model_used,
            mode=payload.mode,
            fallback_used=fallback_used,
            safe_mode_blocked=safe_mode_blocked,
            error=error,
            error_code=error_code,
            correlation_id=payload.correlation_id,
            idempotency_replayed=False,
            elyra=elyra_output,
            elyra_multimodal=multimodal_output,
            elyra_learning=None,
            task_type=strategy.task_type,
            origin_system=payload.origin_system,
            task_criticality=strategy.criticality,
            requires_structured_response=strategy.requires_structured_response,
            response_style=strategy.response_style,
            project_id=project.project_id,
            project_read_only=project.read_only,
            project_can_execute_commands=project.can_execute_commands,
            project_can_write_files=project.can_write_files,
            task_allowed_for_project=policy.allowed,
            artifact_count=artifacts_result.count,
            artifact_types=artifacts_result.types,
            artifact_warnings=artifacts_result.warnings,
            qa_skeleton=qa_skeleton,
            release_gate=release_gate,
            visual_qa_analysis=visual_qa,
            exploration=exploration,
            warning_items=warning_items,
            audit=audit,
            status=status,
            blocked_reason=blocked_reason,
            intelligence_plan=intelligence_plan,
            memory_used=memory_used,
            shadow_decision=shadow_decision,
        )

    async def _execute_local_model(
        self,
        payload: ChatRequest,
        strategy,
        prompt,
        binding: SelectedProviderModel,
    ) -> tuple[str, str, str, bool, str | None, str | None, list[WarningItem]]:
        """Gate do provider generativo local opt-in (PEDROCORE-LOCAL-MODEL-01).

        Só executa quando TODAS as condições valem: allow_local_model=true no
        payload, flag/backend habilitados no ambiente e task não crítica.
        Nunca aprova release gate, nunca usa chave externa e, sem transport
        injetado, nunca faz chamada de rede (fallback Mock controlado).
        """
        items: list[WarningItem] = []

        async def blocked(code: str, message: str):
            items.append(make_warning(code, message))
            answer, provider_used, model_used, fallback_used = (
                await self._mock_fallback(
                    payload,
                    LOCAL_MODEL_PROVIDER_NAME,
                    message,
                    prompt.enriched_system_prompt,
                )
            )
            return (
                answer,
                provider_used,
                model_used,
                fallback_used,
                message,
                code,
                items,
            )

        if not payload.allow_local_model:
            return await blocked(
                codes.LOCAL_MODEL_NOT_AUTHORIZED, LOCAL_MODEL_NOT_AUTHORIZED_WARNING
            )
        if not local_model_ready():
            return await blocked(
                codes.LOCAL_MODEL_DISABLED, LOCAL_MODEL_DISABLED_WARNING
            )
        if (
            strategy.task_type == RELEASE_GATE_TASK_TYPE
            or strategy.criticality == "critical"
        ):
            return await blocked(
                codes.LOCAL_MODEL_TASK_BLOCKED, LOCAL_MODEL_TASK_BLOCKED_WARNING
            )

        provider = provider_registry.get(LOCAL_MODEL_PROVIDER_NAME)
        try:
            result = await self._generate_with_timeout(
                provider,
                payload,
                prompt.enriched_system_prompt,
                binding.model_id,
                strategy.task_type,
            )
            items.append(
                make_warning(
                    codes.LOCAL_MODEL_USED,
                    "Resposta gerada por modelo local opt-in; não usar como "
                    "validação de release gate.",
                )
            )
            return result.answer, result.provider, result.model, False, None, None, items
        except Exception as exc:
            error = str(exc)
            items.append(
                make_warning(codes.LOCAL_MODEL_TRANSPORT_UNAVAILABLE, error)
            )
            answer, provider_used, model_used, fallback_used = (
                await self._mock_fallback(
                    payload,
                    LOCAL_MODEL_PROVIDER_NAME,
                    error,
                    prompt.enriched_system_prompt,
                )
            )
            return (
                answer,
                provider_used,
                model_used,
                fallback_used,
                error,
                None,
                items,
            )

    def _select_auto_real_provider(self, caller, project_id: str):
        """Seleciona provider real disponivel para provider=auto.

        Nesta frente, a politica real autorizada comeca por Gemini. Outros
        providers reais continuam registrados para o chat do Veltrix, mas nao
        entram na decisao auto do contrato FinGuard ate frente propria.

        A lista de candidatos permanece congelada; a autorização por projeto
        apenas NEGA o candidato — nunca promove outro provider real no lugar
        dele. Negado vira fallback Mock seguro, nunca segundo provider real.

        Retorna (provider, decisão negada). Provider None com decisão None
        significa "nenhum provider real configurado".
        """
        for provider_name in AUTO_REAL_PROVIDER_CANDIDATES:
            provider = provider_registry.get(provider_name)
            if provider is None or not provider.real_provider or not provider.is_configured:
                continue
            decision = provider_authorization_service.evaluate(
                identity_strength=caller.identity_strength,
                project_id=project_id,
                caller_role=caller.caller_role,
                environment=caller.environment,
                provider_id=provider.name,
            )
            if decision.denied:
                return None, decision
            return provider, None
        return None, None

    @staticmethod
    def _select_enforced_real_provider(routing_decision, caller, project_id: str):
        """Resolve somente o primeiro sobrevivente produzido pelo motor único."""
        selected = routing_decision.selected_provider
        if not selected:
            return None, None

        provider = provider_registry.get(selected)
        if provider is None or not provider.real_provider or not provider.is_configured:
            return None, None

        decision = provider_authorization_service.evaluate(
            identity_strength=caller.identity_strength,
            project_id=project_id,
            caller_role=caller.caller_role,
            environment=caller.environment,
            provider_id=provider.name,
        )
        if decision.denied:
            return None, decision
        return provider, None

    @staticmethod
    def _routing_unavailable(routing_decision) -> tuple[str, str]:
        """Traduz a eliminação principal para o contrato estável existente."""
        first_reason = next(
            (
                candidate.elimination_reason
                for candidate in routing_decision.candidates_considered
                if candidate.elimination_reason is not None
            ),
            None,
        )
        if first_reason is EliminationReason.AMBIGUOUS_IDENTITY:
            return codes.CALLER_IDENTITY_AMBIGUOUS, PROVIDER_AMBIGUOUS_IDENTITY_WARNING
        if first_reason is EliminationReason.SAFE_MODE_BLOCKED:
            return codes.PROVIDER_REAL_BLOCKED, AUTO_PROVIDER_REAL_BLOCKED_WARNING
        if first_reason is EliminationReason.NOT_AUTHORIZED:
            return (
                codes.PROVIDER_NOT_AUTHORIZED_FOR_PROJECT,
                PROVIDER_NOT_AUTHORIZED_WARNING,
            )
        if first_reason is EliminationReason.NOT_HOMOLOGATED:
            return codes.PROVIDER_NOT_HOMOLOGATED, PROVIDER_NOT_AUTHORIZED_WARNING
        if first_reason in {
            EliminationReason.CIRCUIT_OPEN,
            EliminationReason.HALF_OPEN_BUSY,
        }:
            return codes.PROVIDER_CIRCUIT_OPEN, PROVIDER_CIRCUIT_OPEN_WARNING
        if first_reason in {
            EliminationReason.MODEL_INCOMPATIBLE,
            EliminationReason.MODEL_NOT_HOMOLOGATED,
            EliminationReason.MODEL_NOT_AUTHORIZED,
        }:
            return (
                codes.MODEL_DEFAULT_UNAVAILABLE,
                "Nenhum modelo elegível foi selecionado pela política automática.",
            )
        return codes.PROVIDER_REAL_UNAVAILABLE, PROVIDER_REAL_UNAVAILABLE_WARNING

    @staticmethod
    def _routing_candidates(candidates) -> list[dict[str, object]]:
        return [
            {
                "provider_id": candidate.provider_id,
                "model_id": candidate.model_id,
                "priority": candidate.priority,
                "eliminated": candidate.eliminated,
                "elimination_reason": (
                    candidate.elimination_reason.value
                    if candidate.elimination_reason is not None
                    else None
                ),
            }
            for candidate in candidates
        ]

    @staticmethod
    def _apply_generation_audit(audit) -> None:
        """Consolida orçamento, tempos e término da ÚLTIMA tentativa real.

        Sem tentativa real registrada (Mock, local_qa, bloqueio de policy), os
        campos permanecem nos defaults seguros. Nenhuma métrica é inventada:
        o que o provider não informou continua `None`.
        """
        if not audit.provider_attempts:
            return
        attempt = audit.provider_attempts[-1]

        audit.output_budget_effective = attempt.get("output_budget")
        audit.output_budget_source = attempt.get("budget_source")
        audit.output_budget_clamped = attempt.get("budget_clamped")
        audit.orchestration_timeout_ms = attempt.get("orchestration_timeout_ms")
        audit.transport_timeout_ms = attempt.get("transport_timeout_ms")
        audit.transport_close_requested = bool(
            attempt.get("transport_close_requested")
        )
        audit.transport_close_outcome = str(
            attempt.get("transport_close_outcome")
            or TransportClose.NOT_ATTEMPTED.value
        )
        audit.provider_finish_reason = attempt.get("finish_reason")
        audit.provider_input_tokens = attempt.get("input_tokens")
        audit.provider_output_tokens = attempt.get("output_tokens")
        audit.provider_total_tokens = attempt.get("total_tokens")
        audit.provider_output_truncated = bool(attempt.get("output_truncated"))

        if audit.output_budget_effective is not None:
            audit.output_budget_global_cap = output_budget_service.global_cap()
            audit.output_budget_task_cap = output_budget_service.task_cap(
                audit.task_type
            )
            audit.output_budget_model_cap = (
                provider_catalog_service.max_output_tokens_for(attempt.get("model_id"))
            )

    @staticmethod
    def _provider_failure_signal(exc: Exception) -> tuple[str, str | None, list[WarningItem]]:
        """Traduz a falha estruturada de uma tentativa em contrato estável.

        `error_code` permanece o conjunto já conhecido pelo FinGuard sempre que
        possível: timeout de transporte continua sendo `PROVIDER_TIMEOUT`. Os
        estados novos entram como warnings adicionais, que são aditivos por
        contrato e não quebram consumidor existente.
        """
        error = str(exc)
        error_code: str | None = None
        items: list[WarningItem] = []

        if isinstance(exc, ProviderCircuitOpenError):
            error = PROVIDER_CIRCUIT_OPEN_WARNING
            error_code = codes.PROVIDER_CIRCUIT_OPEN
            items.append(make_warning(codes.PROVIDER_CIRCUIT_OPEN, error))
        elif isinstance(exc, ProviderOutputRejectedError):
            if exc.truncated:
                error = PROVIDER_OUTPUT_TRUNCATED_WARNING
                error_code = codes.PROVIDER_OUTPUT_TRUNCATED
            else:
                error = PROVIDER_OUTPUT_REJECTED_WARNING
                error_code = codes.PROVIDER_OUTPUT_REJECTED
            items.append(make_warning(error_code, error))
        elif isinstance(exc, ProviderTransportTimeoutError):
            # Contrato estável: o consumidor continua vendo PROVIDER_TIMEOUT.
            error = PROVIDER_TIMEOUT_WARNING
            error_code = codes.PROVIDER_TIMEOUT
            items.append(make_warning(codes.PROVIDER_TIMEOUT, error))
            items.append(
                make_warning(
                    codes.PROVIDER_TRANSPORT_TIMEOUT,
                    PROVIDER_TRANSPORT_TIMEOUT_WARNING,
                )
            )
            items.append(
                make_warning(
                    codes.PROVIDER_COMPLETION_AMBIGUOUS,
                    PROVIDER_COMPLETION_AMBIGUOUS_WARNING,
                )
            )
        elif isinstance(exc, TimeoutError):
            error = PROVIDER_TIMEOUT_WARNING
            error_code = codes.PROVIDER_TIMEOUT
            items.append(make_warning(codes.PROVIDER_TIMEOUT, error))
            items.append(
                make_warning(
                    codes.PROVIDER_COMPLETION_AMBIGUOUS,
                    PROVIDER_COMPLETION_AMBIGUOUS_WARNING,
                )
            )
        elif isinstance(exc, ProviderConfigError):
            error_code = codes.PROVIDER_REAL_UNAVAILABLE
            items.append(make_warning(codes.PROVIDER_REAL_UNAVAILABLE, error))

        return error, error_code, items

    @staticmethod
    def _denial_message(decision) -> str:
        """Distingue negação por identidade de negação por projeto/ambiente."""
        if decision.error_code == codes.CALLER_IDENTITY_AMBIGUOUS:
            return PROVIDER_AMBIGUOUS_IDENTITY_WARNING
        return PROVIDER_NOT_AUTHORIZED_WARNING

    @staticmethod
    def _auto_candidate() -> str | None:
        """Candidato do modo automático — congelado em Gemini-only.

        Serve apenas para o binding derivar internamente o modelo do provider
        que o `auto` já escolheria. Não amplia a lista nem reordena nada.
        """
        return AUTO_REAL_PROVIDER_CANDIDATES[0] if AUTO_REAL_PROVIDER_CANDIDATES else None

    @staticmethod
    def _selection_mode(requested_provider: str) -> str:
        if requested_provider in LOCAL_PROVIDERS:
            return SELECTION_MODE_LOCAL
        if requested_provider == AUTO_PROVIDER_NAME:
            return SELECTION_MODE_AUTO
        return SELECTION_MODE_EXPLICIT

    @staticmethod
    def provider_timeout_seconds() -> float:
        """Orçamento temporal da espera da orquestração, em SEGUNDOS."""
        raw = (os.environ.get(PROVIDER_TIMEOUT_ENV) or "30").strip()
        try:
            return min(120.0, max(0.05, float(raw)))
        except ValueError:
            return 30.0

    @staticmethod
    def _provider_timeout_seconds() -> float:
        return OrchestrationService.provider_timeout_seconds()

    @staticmethod
    def _transport_timeout_ms(orchestration_timeout_seconds: float) -> int:
        """Atalho de leitura para a regra central de derivação do transporte."""
        return output_budget_service.transport_timeout_ms(
            orchestration_timeout_seconds
        )

    def generation_plan_for(
        self,
        provider,
        model: str,
        task_type: str,
        orchestration_timeout_seconds: float | None = None,
    ) -> tuple[OutputBudget | None, int | None]:
        """Resolve orçamento de saída e timeout de transporte da tentativa.

        Só se aplica a adapters que declaram `supports_generation_budget`.
        Mock, `local_qa` e `local_model` seguem exatamente o caminho anterior.
        Nada aqui lê payload, metadata ou contexto: o consumidor não participa
        da decisão de orçamento.
        """
        if not getattr(provider, "supports_generation_budget", False):
            return None, None
        if orchestration_timeout_seconds is None:
            orchestration_timeout_seconds = self._provider_timeout_seconds()
        budget = output_budget_service.resolve(
            task_type=task_type,
            model_cap=provider_catalog_service.max_output_tokens_for(model),
        )
        return budget, self._transport_timeout_ms(orchestration_timeout_seconds)

    @staticmethod
    def _real_fallback_enabled() -> bool:
        return (
            os.environ.get(FLAG_REAL_FALLBACK_ENABLED) or ""
        ).strip().lower() == "true"

    @staticmethod
    def _safe_for_real_fallback(attempt: dict[str, object]) -> bool:
        return (
            attempt.get("failure_classification")
            in REAL_FALLBACK_SAFE_CLASSIFICATIONS
            and attempt.get("completion_certainty")
            == CompletionCertainty.NOT_DISPATCHED.value
            and attempt.get("external_dispatch") is False
        )

    def _real_fallback_gate(self, audit, task_type: str) -> tuple[bool, str]:
        attempt = audit.provider_attempts[-1] if audit.provider_attempts else None

        if not audit.real_fallback_enabled:
            reason = REAL_FALLBACK_DISABLED_REASON
        elif task_type not in REAL_FALLBACK_ALLOWED_TASKS:
            reason = REAL_FALLBACK_TASK_BLOCKED_REASON
        elif len(audit.provider_attempts) >= MAX_REAL_PROVIDER_ATTEMPTS:
            reason = REAL_FALLBACK_MAX_ATTEMPTS_REASON
        elif attempt is None or not self._safe_for_real_fallback(attempt):
            reason = REAL_FALLBACK_UNSAFE_FAILURE_REASON
        else:
            reason = REAL_FALLBACK_STARTED_REASON

        allowed = reason == REAL_FALLBACK_STARTED_REASON
        if attempt is not None:
            attempt["fallback_eligible"] = allowed
            attempt["fallback_decision_reason"] = reason
        return allowed, reason

    async def _try_enforced_real_fallback(
        self,
        *,
        primary_provider,
        payload: ChatRequest,
        enriched_system_prompt: str,
        caller,
        identity_project_id: str,
        context_project_id: str,
        task_type: str,
        policy_allowed: bool,
        audit,
    ) -> ProviderResponse | None:
        """Tenta um único secundário após término pre-dispatch comprovado.

        Não há loop, task em background, race ou hedging. O método só é chamado
        depois que a tentativa primária retornou uma exception estruturada.
        """
        allowed, reason = self._real_fallback_gate(audit, task_type)
        audit.real_fallback_reason = reason
        if not allowed:
            return None

        secondary_decision = shadow_routing_service.evaluate(
            caller=caller,
            identity_project_id=identity_project_id,
            context_project_id=context_project_id,
            task_type=task_type,
            allow_real_provider=payload.allow_real_provider,
            policy_allowed=policy_allowed,
            excluded_provider_ids=frozenset({primary_provider.name}),
        )
        audit.real_fallback_candidates_considered = self._routing_candidates(
            secondary_decision.candidates_considered
        )
        audit.real_fallback_candidates_eliminated = self._routing_candidates(
            secondary_decision.candidates_eliminated
        )

        if (
            secondary_decision.selected_provider is None
            or secondary_decision.selected_provider == primary_provider.name
            or secondary_decision.selected_model is None
        ):
            audit.real_fallback_reason = REAL_FALLBACK_NO_CANDIDATE_REASON
            audit.provider_attempts[-1]["fallback_eligible"] = False
            audit.provider_attempts[-1][
                "fallback_decision_reason"
            ] = REAL_FALLBACK_NO_CANDIDATE_REASON
            return None

        secondary_binding = provider_binding_service.resolve(
            requested_provider=AUTO_PROVIDER_NAME,
            requested_model=None,
            selection_mode=SELECTION_MODE_AUTO,
            caller_role=caller.caller_role,
            task_type=task_type,
            auto_candidate=secondary_decision.selected_provider,
        )
        if (
            secondary_binding.invalid
            or secondary_binding.model_id is None
            or secondary_binding.model_id != secondary_decision.selected_model
        ):
            audit.real_fallback_reason = REAL_FALLBACK_NO_CANDIDATE_REASON
            audit.provider_attempts[-1]["fallback_eligible"] = False
            audit.provider_attempts[-1][
                "fallback_decision_reason"
            ] = REAL_FALLBACK_NO_CANDIDATE_REASON
            return None

        secondary, denial = self._select_enforced_real_provider(
            secondary_decision,
            caller=caller,
            project_id=identity_project_id,
        )
        if secondary is None or denial is not None:
            audit.real_fallback_reason = REAL_FALLBACK_NO_CANDIDATE_REASON
            audit.provider_attempts[-1]["fallback_eligible"] = False
            audit.provider_attempts[-1][
                "fallback_decision_reason"
            ] = REAL_FALLBACK_NO_CANDIDATE_REASON
            return None

        audit.real_fallback_attempted = True
        try:
            result = await self._generate_real_attempt(
                secondary,
                payload,
                enriched_system_prompt,
                secondary_binding.model_id,
                audit=audit,
                environment=caller.environment,
                ordinal=2,
                selection_reason=secondary_decision.selection_reason,
                fallback_candidate=False,
                task_type=task_type,
            )
        except Exception:
            audit.real_fallback_reason = (
                "Provider secundário falhou; Mock seguro aplicado sem terceira tentativa."
            )
            if audit.provider_attempts:
                audit.provider_attempts[-1][
                    "fallback_decision_reason"
                ] = REAL_FALLBACK_MAX_ATTEMPTS_REASON
                audit.provider_attempts[-1]["fallback_eligible"] = False
            return None

        audit.real_fallback_reason = "Provider secundário concluiu com sucesso."
        audit.provider_attempts[-1][
            "fallback_decision_reason"
        ] = "Sucesso secundário encerrou o fluxo."
        audit.provider_attempts[-1]["fallback_eligible"] = False
        return result

    async def _generate_real_attempt(
        self,
        provider,
        payload: ChatRequest,
        enriched_system_prompt: str,
        model: str,
        *,
        audit,
        environment: str,
        ordinal: int,
        selection_reason: str,
        fallback_candidate: bool,
        task_type: str,
    ):
        """Executa uma tentativa identificada e atualiza o circuito.

        A classificação é baseada em tipos estruturados, nunca em texto de
        exception. Qualquer expiração de tempo após o dispatch — a espera da
        orquestração (``TimeoutError``) ou o transporte HTTP
        (``ProviderTransportTimeoutError``) — permanece conclusão AMBÍGUA:
        encerrar a espera ou fechar a conexão local não prova que a geração
        remota parou.
        """
        attempt_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        started = time.perf_counter()
        key = provider_health_service.key(environment, provider.name, model)
        permit = provider_health_service.acquire(key)
        before = permit.snapshot
        orchestration_timeout = self._provider_timeout_seconds()
        plan = self.generation_plan_for(
            provider, model, task_type, orchestration_timeout
        )
        budget, transport_timeout_ms = plan
        supports_cancel = bool(
            getattr(provider, "supports_transport_cancellation", False)
        )

        attempt = {
            "request_id": audit.audit_id,
            "attempt_id": attempt_id,
            "ordinal": ordinal,
            "provider_id": provider.name,
            "model_id": model,
            "selection_reason": selection_reason,
            "started_at": started_at,
            "circuit_state_before": before.state.value,
            "consecutive_failures_before": before.consecutive_failures,
            "cooldown_remaining_before": before.cooldown_remaining_seconds,
            "half_open_probe": permit.half_open_probe,
            "external_dispatch": False,
            "completion_certainty": CompletionCertainty.NOT_DISPATCHED.value,
            "failure_classification": None,
            "result": None,
            "fallback_eligible": False,
            "fallback_classification_safe": False,
            "fallback_decision_reason": (
                None
                if fallback_candidate
                else "Fallback real não se aplica a esta seleção."
            ),
            # Orçamento e tempo decididos pelo Veltrix para esta tentativa.
            "output_budget": budget.effective_budget if budget is not None else None,
            "budget_source": (
                budget.budget_source.value if budget is not None else None
            ),
            "budget_clamped": budget.budget_clamped if budget is not None else None,
            "orchestration_timeout_ms": int(orchestration_timeout * 1_000),
            "transport_timeout_ms": transport_timeout_ms,
            # Fatos de transporte LOCAL. Nunca são prova de término remoto.
            # Solicitar o fechamento e confirmá-lo são fatos distintos: o
            # `outcome` só vira `confirmed` quando o adapter observou o
            # fechamento de verdade.
            "transport_close_requested": False,
            "transport_close_outcome": TransportClose.NOT_ATTEMPTED.value,
            # Metadados de término, preenchidos quando o provider os fornece.
            "finish_reason": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "output_truncated": False,
        }

        def finish(
            *,
            classification: FailureClassification,
            certainty: CompletionCertainty,
            external_dispatch: bool,
            result: str,
            after,
        ) -> None:
            attempt.update(
                {
                    "external_dispatch": external_dispatch,
                    "completion_certainty": certainty.value,
                    "failure_classification": classification.value,
                    "result": result,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "duration_ms": round((time.perf_counter() - started) * 1_000, 2),
                    "circuit_state_after": after.state.value,
                    "consecutive_failures_after": after.consecutive_failures,
                    "opened_at_monotonic": after.opened_at_monotonic,
                    "cooldown_remaining_after": after.cooldown_remaining_seconds,
                }
            )
            attempt["fallback_classification_safe"] = (
                classification.value in REAL_FALLBACK_SAFE_CLASSIFICATIONS
                and certainty is CompletionCertainty.NOT_DISPATCHED
                and external_dispatch is False
            )
            if result == "success" and fallback_candidate:
                attempt["fallback_decision_reason"] = (
                    "Sucesso primário; provider secundário não necessário."
                )
            audit.provider_attempts.append(attempt)

        if not permit.allowed:
            after = provider_health_service.peek(key)
            finish(
                classification=FailureClassification.PROVIDER_PRE_DISPATCH,
                certainty=CompletionCertainty.NOT_DISPATCHED,
                external_dispatch=False,
                result="circuit_blocked",
                after=after,
            )
            raise ProviderCircuitOpenError(permit.reason or PROVIDER_CIRCUIT_OPEN_WARNING)

        try:
            result = await self._generate_with_timeout(
                provider,
                payload,
                enriched_system_prompt,
                model,
                task_type,
                plan=plan,
            )
        except Exception as exc:
            classification, certainty, external_dispatch = (
                self._classify_provider_failure(exc)
            )
            if isinstance(exc, ProviderOutputRejectedError):
                attempt["finish_reason"] = exc.finish_reason
                attempt["output_truncated"] = exc.truncated
                # O custo já foi incorrido: os metadados não se perdem.
                attempt["input_tokens"] = exc.input_tokens
                attempt["output_tokens"] = exc.output_tokens
                attempt["total_tokens"] = exc.total_tokens
            if external_dispatch and supports_cancel:
                # O fechamento foi solicitado. O RESULTADO só é conhecido
                # quando o próprio adapter o observou e anexou à exceção;
                # quando `asyncio.wait_for` cancela, a exceção que chega aqui
                # é do `wait_for` e o resultado é honestamente desconhecido.
                attempt["transport_close_requested"] = True
                attempt["transport_close_outcome"] = getattr(
                    exc, "transport_close", TransportClose.UNKNOWN
                ).value
            after = provider_health_service.record(
                key,
                classification,
                half_open_probe=permit.half_open_probe,
            )
            finish(
                classification=classification,
                certainty=certainty,
                external_dispatch=external_dispatch,
                result="failed",
                after=after,
            )
            raise

        attempt["finish_reason"] = getattr(result, "finish_reason", None)
        attempt["input_tokens"] = getattr(result, "input_tokens", None)
        attempt["output_tokens"] = getattr(result, "output_tokens", None)
        attempt["total_tokens"] = getattr(result, "total_tokens", None)
        attempt["output_truncated"] = bool(getattr(result, "truncated", False))
        close_outcome = getattr(result, "transport_close", TransportClose.NOT_ATTEMPTED)
        attempt["transport_close_requested"] = (
            close_outcome is not TransportClose.NOT_ATTEMPTED
        )
        attempt["transport_close_outcome"] = close_outcome.value
        after = provider_health_service.record(
            key,
            FailureClassification.SUCCESS,
            half_open_probe=permit.half_open_probe,
        )
        finish(
            classification=FailureClassification.SUCCESS,
            certainty=CompletionCertainty.COMPLETED,
            external_dispatch=True,
            result="success",
            after=after,
        )
        return result

    @staticmethod
    def _classify_provider_failure(
        error: Exception,
    ) -> tuple[FailureClassification, CompletionCertainty, bool]:
        if isinstance(error, ProviderTransportTimeoutError):
            # O transporte local expirou e a conexão foi encerrada. Isso NÃO é
            # prova de que a geração remota parou: a certeza continua ambígua,
            # exatamente como no timeout da orquestração.
            return (
                FailureClassification.COMPLETION_AMBIGUOUS,
                CompletionCertainty.AMBIGUOUS,
                True,
            )
        if isinstance(error, ProviderOutputRejectedError):
            # A chamada externa TERMINOU: a resposta chegou, mas não é
            # utilizável (truncada por orçamento ou finish_reason anormal).
            # `provider_non_retryable` não degrada o circuito e não é
            # classificação segura para provider secundário.
            return (
                FailureClassification.PROVIDER_NON_RETRYABLE,
                CompletionCertainty.COMPLETED,
                True,
            )
        if isinstance(error, TimeoutError):
            return (
                FailureClassification.COMPLETION_AMBIGUOUS,
                CompletionCertainty.AMBIGUOUS,
                True,
            )
        if isinstance(error, ProviderConfigError):
            return (
                FailureClassification.PROVIDER_PRE_DISPATCH,
                CompletionCertainty.NOT_DISPATCHED,
                False,
            )
        if isinstance(error, ProviderExecutionError):
            return (
                FailureClassification.PROVIDER_RETRYABLE,
                CompletionCertainty.COMPLETED,
                True,
            )
        return (
            FailureClassification.INTERNAL_ERROR,
            CompletionCertainty.AMBIGUOUS,
            True,
        )

    async def _generate_with_timeout(
        self,
        provider,
        payload: ChatRequest,
        enriched_system_prompt: str,
        model: str,
        task_type: str,
        plan: tuple[OutputBudget | None, int | None] | None = None,
    ):
        """Executa o adapter com o modelo JÁ VALIDADO pelo binding.

        O adapter nunca recebe `payload.model` diretamente: só a combinação
        provider+modelo aprovada pelo Veltrix chega até aqui. O mesmo vale
        para o orçamento de saída e o timeout de transporte, ambos resolvidos
        internamente e nunca influenciados pelo consumidor.
        """
        if not isinstance(model, str) or not model.strip():
            raise ProviderExecutionError(
                "Adapter não pode executar sem model_id validado pelo Veltrix."
            )

        orchestration_timeout = self._provider_timeout_seconds()
        if plan is None:
            plan = self.generation_plan_for(
                provider, model, task_type, orchestration_timeout
            )
        budget, transport_timeout_ms = plan

        generation_kwargs: dict[str, int] = {}
        if budget is not None and transport_timeout_ms is not None:
            generation_kwargs["output_budget"] = budget.effective_budget
            generation_kwargs["transport_timeout_ms"] = transport_timeout_ms

        return await asyncio.wait_for(
            provider.generate_response(
                message=payload.message,
                mode=payload.mode,
                model=model,
                system_prompt=enriched_system_prompt,
                **generation_kwargs,
            ),
            timeout=orchestration_timeout,
        )

    def build_assistant_payload(
        self, outcome: OrchestrationOutcome
    ) -> AssistantResponsePayload:
        """Projeção de assistente para sistemas consumidores do ecossistema."""
        plan = outcome.intelligence_plan
        evaluation = (
            evaluation_service.evaluate_intelligence_plan(plan).model_dump()
            if plan is not None
            else None
        )
        suggestions: list[str] = []
        if outcome.qa_skeleton is not None:
            suggestions = list(outcome.qa_skeleton.suggested_fixes)

        return AssistantResponsePayload(
            answer=outcome.answer,
            suggestions=suggestions,
            disclaimer=(
                FINANCIAL_DISCLAIMER_TEXT
                if outcome.task_type == FINANCE_ADVICE_TASK_TYPE
                else None
            ),
            safety_flags=list(plan.safety_flags) if plan is not None else [],
            provider_used=outcome.provider_used,
            model=outcome.model,
            audit_id=outcome.audit.audit_id,
            memory_used=outcome.memory_used,
            evaluation=evaluation,
            warnings=outcome.warning_items,
        )

    def _apply_artifact_reader(
        self, payload: ChatRequest
    ) -> tuple[list[ArtifactInput] | None, list[WarningItem]]:
        """Converte artefatos com path allowlisted em artefatos textuais (Bloco 9).

        Regras: nunca para origem FinGuard; nunca com o reader desabilitado.
        Em qualquer falha, o artefato original segue para o ArtifactService,
        que o rejeita com ARTIFACT_PATH_REJECTED (comportamento pré-existente).
        """
        if not payload.artifacts:
            return payload.artifacts, []

        path_requests = []
        for artifact in payload.artifacts:
            metadata_keys = (
                {str(key).strip().lower() for key in artifact.metadata}
                if artifact.metadata
                else set()
            )
            path_keys = metadata_keys & PATH_LIKE_METADATA_KEYS
            path_requests.append(sorted(path_keys)[0] if path_keys else None)

        if not any(path_requests):
            return payload.artifacts, []

        origin = (payload.origin_system or "").strip().lower()
        if origin in FINGUARD_ORIGIN_SYSTEMS:
            return payload.artifacts, [
                make_warning(
                    codes.ARTIFACT_READER_PATH_NOT_ALLOWED,
                    READER_FINGUARD_ORIGIN_WARNING,
                )
            ]

        if not artifact_reader_service.is_enabled():
            return payload.artifacts, [
                make_warning(
                    codes.ARTIFACT_READER_DISABLED,
                    "Artifact Reader desabilitado; leitura por path não realizada.",
                )
            ]

        items: list[WarningItem] = []
        effective: list[ArtifactInput] = []
        remaining_budget = artifact_reader_service.max_total_chars()

        for artifact, path_key in zip(payload.artifacts, path_requests):
            if path_key is None:
                effective.append(artifact)
                continue

            requested_path = str(artifact.metadata.get(path_key, ""))
            result = artifact_reader_service.read(
                requested_path, remaining_budget=remaining_budget
            )

            for code, message in zip(result.warning_codes, result.warnings):
                items.append(make_warning(code, message))

            if result.allowed and result.content is not None:
                remaining_budget -= result.chars_read
                effective.append(
                    ArtifactInput(
                        type="text",
                        name=result.file_name or artifact.name,
                        content=result.content,
                        metadata=None,
                    )
                )
            else:
                effective.append(artifact)

        return effective, items

    def _elyra_learning_outcome(
        self,
        *,
        payload: ChatRequest,
        caller: AuthenticatedCallerContext,
        strategy,
        project,
        policy,
        origin_claim: OriginClaimResult,
        started: float,
    ) -> OrchestrationOutcome:
        """Executa submissao ou revogacao governada, sem tocar em provider."""
        # Import tardio por fronteira de plano — ver ADR-PEDROCORE-CONTROL-PLANE-01
        # e `app/architecture/planes.py`. Esta e a UNICA funcao do Runtime Plane
        # que alcanca a maquinaria do Learning Plane, e ela nunca executa provider.
        from app.modules.training_data.acquisition import (
            TrainingCandidateTransitionError,
            training_candidate_service,
        )

        validation = elyra_learning_service.validate_input(payload, caller)
        if not validation.valid:
            return self._elyra_contract_blocked_outcome(
                payload=payload,
                caller=caller,
                error_code=(
                    validation.error_code or codes.ELYRA_LEARNING_INPUT_SCHEMA_INVALID
                ),
                reason=validation.reason or "Contrato de learning Elyra inválido.",
                started=started,
            )

        try:
            if validation.submission is not None:
                proposal = elyra_learning_service.build_proposal(
                    validation.submission, caller.credential_id
                )
                record, duplicate = training_candidate_service.submit_external(
                    proposal,
                    fingerprint=validation.submission.fingerprint,
                    training_purpose=TrainingPurpose.EVALUATION_ONLY,
                )
                operation = SUBMIT_OPERATION
            else:
                revocation = validation.revocation
                assert revocation is not None
                record, changed = training_candidate_service.revoke_external(
                    project_id="elyra",
                    source_type=TrainingSourceType.ELYRA_REPORT_SNAPSHOT,
                    training_purpose=TrainingPurpose.EVALUATION_ONLY,
                    fingerprint=revocation.fingerprint,
                    reason_code=revocation.reason_code,
                    revoked_by=caller.credential_id,
                )
                # Revogar de novo nao e novidade nem erro: e replay governado.
                duplicate = not changed
                operation = REVOKE_OPERATION
        except TrainingCandidateTransitionError as error:
            code = (
                codes.ELYRA_LEARNING_CANDIDATE_NOT_FOUND
                if str(error) == "CANDIDATE_NOT_FOUND"
                else codes.ELYRA_LEARNING_INTERNAL_FAILURE
            )
            reason = (
                LEARNING_NOT_FOUND_REASON
                if code == codes.ELYRA_LEARNING_CANDIDATE_NOT_FOUND
                else LEARNING_INTERNAL_FAILURE_REASON
            )
            return self._elyra_contract_blocked_outcome(
                payload=payload,
                caller=caller,
                error_code=code,
                reason=reason,
                started=started,
            )

        receipt = elyra_learning_service.receipt(
            operation=operation,
            correlation_id=payload.correlation_id or "",
            candidate_id=record.candidate_id,
            lifecycle=record.lifecycle.value,
            duplicate=duplicate,
        )

        audit = audit_service.create(
            origin_system=payload.origin_system,
            task_type=strategy.task_type,
            provider_requested="none",
            criticality=strategy.criticality,
            caller=caller,
            origin_claim=origin_claim,
            provider_selection_mode=self._selection_mode(payload.provider),
            correlation_id=payload.correlation_id,
            idempotency_key=payload.idempotency_key,
        )
        audit.fallback_used = False
        audit.provider_used = "none"
        audit.status = "ok"
        audit.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        audit.can_advance = True
        audit.authorization_result = "allowed"

        return OrchestrationOutcome(
            # O recibo nao devolve o payload submetido: so o estado governado.
            answer=(
                f"Candidato {record.candidate_id} registrado em "
                f"{record.lifecycle.value}."
            ),
            provider_requested="none",
            provider_used="none",
            model="none",
            mode=payload.mode,
            fallback_used=False,
            safe_mode_blocked=False,
            error=None,
            error_code=None,
            task_type=strategy.task_type,
            origin_system=payload.origin_system,
            task_criticality=strategy.criticality,
            requires_structured_response=strategy.requires_structured_response,
            response_style=strategy.response_style,
            project_id=project.project_id,
            project_read_only=project.read_only,
            project_can_execute_commands=project.can_execute_commands,
            project_can_write_files=project.can_write_files,
            task_allowed_for_project=policy.allowed,
            artifact_count=0,
            artifact_types=[],
            artifact_warnings=[],
            warning_items=[],
            audit=audit,
            status="ok",
            blocked_reason=None,
            correlation_id=payload.correlation_id,
            idempotency_replayed=False,
            elyra=None,
            elyra_multimodal=None,
            elyra_learning=receipt,
        )

    def _elyra_contract_blocked_outcome(
        self,
        *,
        payload: ChatRequest,
        caller: AuthenticatedCallerContext,
        error_code: str,
        reason: str,
        started: float,
        provider_used: str = "none",
    ) -> OrchestrationOutcome:
        """Bloqueio do boundary Elyra sem provider/fallback ou conteúdo parcial."""
        strategy = task_router.resolve(payload.task_type)
        project = project_context_resolver.resolve(payload.origin_system)
        origin_claim = caller_identity_service.validate_origin_claim(
            caller,
            payload.origin_system,
            project.project_id,
        )
        policy = project_context_resolver.evaluate_task_policy(project, strategy.task_type)
        audit = audit_service.create(
            origin_system=payload.origin_system,
            task_type=strategy.task_type,
            provider_requested=(payload.provider or settings.default_provider).lower(),
            criticality=strategy.criticality,
            caller=caller,
            origin_claim=origin_claim,
            provider_selection_mode=self._selection_mode(payload.provider),
            correlation_id=payload.correlation_id,
            idempotency_key=payload.idempotency_key,
        )
        audit.fallback_used = False
        audit.provider_used = provider_used
        audit.status = "blocked"
        audit.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        audit.can_advance = False
        audit.authorization_result = "denied"
        audit.authorization_reason_code = error_code

        return OrchestrationOutcome(
            answer="Solicitação Elyra bloqueada pelo contrato V1 da capability.",
            provider_requested=(payload.provider or settings.default_provider).lower(),
            provider_used=provider_used,
            model="none",
            mode=payload.mode,
            fallback_used=False,
            safe_mode_blocked=False,
            error=reason,
            error_code=error_code,
            task_type=strategy.task_type,
            origin_system=payload.origin_system,
            task_criticality=strategy.criticality,
            requires_structured_response=strategy.requires_structured_response,
            response_style=strategy.response_style,
            project_id=project.project_id,
            project_read_only=project.read_only,
            project_can_execute_commands=project.can_execute_commands,
            project_can_write_files=project.can_write_files,
            task_allowed_for_project=policy.allowed,
            artifact_count=0,
            artifact_types=[],
            artifact_warnings=[],
            warning_items=[make_warning(error_code, reason)],
            audit=audit,
            status="blocked",
            blocked_reason=reason,
            correlation_id=payload.correlation_id,
            idempotency_replayed=False,
            elyra=None,
            elyra_multimodal=None,
            elyra_learning=None,
        )

    def _identity_blocked_outcome(
        self,
        payload: ChatRequest,
        strategy,
        project,
        caller: AuthenticatedCallerContext,
        origin_claim: OriginClaimResult,
        requested_provider: str,
        error_code: str,
        reason: str,
        started: float,
        answer_prefix: str = IDENTITY_BLOCKED_ANSWER_PREFIX,
        binding: SelectedProviderModel | None = None,
    ) -> OrchestrationOutcome:
        """Bloqueio por identidade/autorização do caller ou por binding inválido.

        Acontece ANTES de qualquer provider: origem incompatível com a
        credencial autenticada, consumidor comum tentando escolher provider ou
        modelo, ou combinação provider+modelo incoerente. Nenhum adapter real
        é alcançado.
        """
        audit = audit_service.create(
            origin_system=payload.origin_system,
            task_type=strategy.task_type,
            provider_requested=requested_provider,
            criticality=strategy.criticality,
            caller=caller,
            origin_claim=origin_claim,
            provider_selection_mode=self._selection_mode(requested_provider),
            binding=binding,
            correlation_id=payload.correlation_id,
            idempotency_key=payload.idempotency_key,
        )
        audit.fallback_used = False
        audit.provider_used = "none"
        audit.safe_mode_blocked = False
        audit.status = "blocked"
        audit.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        audit.can_advance = False
        audit.authorization_result = "denied"
        audit.authorization_reason_code = error_code

        return OrchestrationOutcome(
            answer=f"{answer_prefix} Motivo: {reason}",
            provider_requested=requested_provider,
            provider_used="none",
            model="none",
            mode=payload.mode,
            fallback_used=False,
            safe_mode_blocked=False,
            error=reason,
            error_code=error_code,
            task_type=strategy.task_type,
            origin_system=payload.origin_system,
            task_criticality=strategy.criticality,
            requires_structured_response=strategy.requires_structured_response,
            response_style=strategy.response_style,
            project_id=project.project_id,
            project_read_only=project.read_only,
            project_can_execute_commands=project.can_execute_commands,
            project_can_write_files=project.can_write_files,
            task_allowed_for_project=False,
            artifact_count=0,
            artifact_types=[],
            artifact_warnings=[],
            qa_skeleton=None,
            release_gate=None,
            visual_qa_analysis=None,
            exploration=None,
            warning_items=[make_warning(error_code, reason)],
            audit=audit,
            status="blocked",
            blocked_reason=reason,
            correlation_id=payload.correlation_id,
            idempotency_replayed=False,
            elyra=None,
        )

    def _policy_blocked_outcome(
        self,
        payload: ChatRequest,
        strategy,
        project,
        policy,
        enforcement,
        requested_provider: str,
        started: float,
        caller: AuthenticatedCallerContext | None = None,
        origin_claim: OriginClaimResult | None = None,
    ) -> OrchestrationOutcome:
        """Bloqueio real por policy: nenhum provider, reader ou análise é executado."""
        audit = audit_service.create(
            origin_system=payload.origin_system,
            task_type=strategy.task_type,
            provider_requested=requested_provider,
            criticality=strategy.criticality,
            caller=caller,
            origin_claim=origin_claim,
            provider_selection_mode=self._selection_mode(requested_provider),
            correlation_id=payload.correlation_id,
            idempotency_key=payload.idempotency_key,
        )
        audit.fallback_used = False
        audit.provider_used = "none"
        audit.safe_mode_blocked = False
        audit.status = "blocked"
        audit.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        audit.can_advance = False

        items: list[WarningItem] = []
        for message in project.warnings:
            items.append(make_warning(codes.UNKNOWN_ORIGIN_SYSTEM, message))
        for message in policy.warnings:
            items.append(make_warning(codes.PROJECT_TASK_NOT_ALLOWED, message))
        for code, message in zip(enforcement.warning_codes, enforcement.warnings):
            items.append(make_warning(code, message))

        answer = (
            "Solicitação bloqueada por policy do Veltrix. "
            f"Motivo: {enforcement.blocked_reason}"
        )

        return OrchestrationOutcome(
            answer=answer,
            provider_requested=requested_provider,
            provider_used="none",
            model="none",
            mode=payload.mode,
            fallback_used=False,
            safe_mode_blocked=False,
            error=enforcement.blocked_reason,
            error_code=enforcement.error_code,
            task_type=strategy.task_type,
            origin_system=payload.origin_system,
            task_criticality=strategy.criticality,
            requires_structured_response=strategy.requires_structured_response,
            response_style=strategy.response_style,
            project_id=project.project_id,
            project_read_only=project.read_only,
            project_can_execute_commands=project.can_execute_commands,
            project_can_write_files=project.can_write_files,
            task_allowed_for_project=policy.allowed,
            artifact_count=0,
            artifact_types=[],
            artifact_warnings=[],
            qa_skeleton=None,
            release_gate=None,
            visual_qa_analysis=None,
            exploration=None,
            warning_items=items,
            audit=audit,
            status="blocked",
            blocked_reason=enforcement.blocked_reason,
            correlation_id=payload.correlation_id,
            idempotency_replayed=False,
            elyra=None,
        )

    async def _mock_fallback(
        self,
        payload: ChatRequest,
        requested_provider: str,
        error: str,
        enriched_system_prompt: str,
    ) -> tuple[str, str, str, bool]:
        """Fallback seguro e conservador quando o provider solicitado falha,
        não está configurado ou foi bloqueado.

        A resposta ao usuário final (`answer`) nunca expõe erro técnico bruto,
        nome de classe de provider/exception, nem texto de debug — isso
        continua disponível só para quem consome `error`/`error_code`/
        `warning_codes`/`audit` (backend, logs, QA), nunca na conversa.

        `allow_mock_fallback=false` é um opt-out restritivo: a falha original
        segue estruturada em `error`/`error_code`/`audit`, nenhum adapter Mock é
        representado como sucesso e o chamador recebe provider/model `none`.
        """
        del requested_provider, error, enriched_system_prompt
        blocked_answer, fallback_answer = self._fallback_answers(payload)
        if not payload.allow_mock_fallback:
            return blocked_answer, "none", "none", False
        return fallback_answer, "mock", "mock-v1", True

    @staticmethod
    def _fallback_answers(payload: ChatRequest) -> tuple[str, str]:
        """Escolhe (resposta sem fallback, resposta com fallback) pelo contexto.

        O disclaimer financeiro pertence ao fluxo financeiro do FinGuard. Em
        chat geral ele confunde: o usuario pergunta o que foi feito no sistema
        e recebe uma garantia sobre movimentacao de dinheiro que nunca esteve
        em jogo.
        """
        origin = (payload.origin_system or "").strip().lower()
        if origin in FINGUARD_ORIGIN_SYSTEMS:
            return NO_MOCK_FALLBACK_ANSWER, SAFE_FALLBACK_ANSWER
        return GENERAL_NO_MOCK_FALLBACK_ANSWER, GENERAL_FALLBACK_ANSWER

    def _collect_warnings(
        self,
        strategy,
        project_warnings: list[str],
        policy_warnings: list[str],
        artifacts_result: ArtifactProcessingResult,
        analysis,
        release_gate,
        provider_used: str,
        fallback_used: bool,
        safe_mode_blocked: bool,
        reader_items: list[WarningItem] | None = None,
        visual_qa=None,
        exploration=None,
        memory_items: list[WarningItem] | None = None,
        local_model_items: list[WarningItem] | None = None,
        provider_items: list[WarningItem] | None = None,
    ) -> list[WarningItem]:
        items: list[WarningItem] = []
        seen: set[tuple[str, str]] = set()

        def add(code: str, message: str, severity: str | None = None) -> None:
            key = (code, message)
            if key in seen:
                return
            seen.add(key)
            items.append(make_warning(code, message, severity))

        for message in strategy.warnings:
            add(codes.UNKNOWN_TASK_TYPE, message)

        for message in project_warnings:
            add(codes.UNKNOWN_ORIGIN_SYSTEM, message)

        for message in policy_warnings:
            if message == TASK_NOT_ALLOWED_WARNING:
                add(codes.PROJECT_TASK_NOT_ALLOWED, message)
            elif message == UNKNOWN_PROJECT_POLICY_WARNING:
                add(codes.UNKNOWN_ORIGIN_SYSTEM, message)
            elif message == EMPTY_ALLOWED_TASKS_WARNING:
                add(codes.PROJECT_POLICY_NOT_ENFORCED, message)
            else:
                add(codes.PROJECT_POLICY_NOT_ENFORCED, message)

        for code, message in zip(
            artifacts_result.warning_codes, artifacts_result.warnings
        ):
            add(code, message)

        if strategy.task_type in CRITICAL_TASK_TYPES and artifacts_result.count == 0:
            add(codes.QA_NO_ARTIFACTS, QA_NO_ARTIFACTS_WARNING)

        if safe_mode_blocked:
            severity = (
                codes.SEVERITY_ERROR
                if strategy.criticality in {"high", "critical"}
                else codes.SEVERITY_WARNING
            )
            add(codes.PROVIDER_REAL_BLOCKED, PROVIDER_REAL_BLOCKED_WARNING, severity)

        if fallback_used and strategy.task_type in CRITICAL_TASK_TYPES:
            add(codes.QA_FALLBACK_MOCK, FALLBACK_CRITICAL_WARNING)
        elif provider_used == "mock" and not strategy.allow_mock:
            add(codes.QA_FALLBACK_MOCK, MOCK_CRITICAL_WARNING)

        if analysis is not None:
            for code, message in zip(analysis.warning_codes, analysis.warnings):
                add(code, message)

        if release_gate is not None:
            for code in release_gate.warning_codes:
                if code == codes.RELEASE_GATE_BLOCKED:
                    add(
                        codes.RELEASE_GATE_BLOCKED,
                        f"Release gate bloqueado: {release_gate.blocked_reason}",
                    )
                else:
                    add(code, release_gate.blocked_reason or "Release gate: ver detalhes.")

        if reader_items:
            for item in reader_items:
                add(item.code, item.message, item.severity)

        if visual_qa is not None:
            for code, message in zip(visual_qa.warning_codes, visual_qa.warnings):
                add(code, message)
            if (
                release_gate is not None
                and not release_gate.can_advance
                and (analysis is None or not analysis.analyzed)
            ):
                add(
                    codes.VISUAL_QA_BLOCKED_FOR_RELEASE_GATE,
                    VISUAL_ONLY_RELEASE_GATE_WARNING,
                )

        if exploration is not None:
            for code, message in zip(exploration.warning_codes, exploration.warnings):
                add(code, message)

        if memory_items:
            for item in memory_items:
                add(item.code, item.message, item.severity)

        if local_model_items:
            for item in local_model_items:
                add(item.code, item.message, item.severity)

        if provider_items:
            for item in provider_items:
                add(item.code, item.message, item.severity)

        if strategy.task_type == FINANCE_ADVICE_TASK_TYPE:
            add(
                codes.FINANCIAL_DISCLAIMER,
                "Resposta financeira conservadora com disclaimer obrigatório; "
                "nenhuma ação financeira é executada.",
            )

        if strategy.task_type in REPORT_MEMORY_TASK_TYPES:
            add(codes.REPORT_MEMORY_IS_NOT_TRAINING, REPORT_NOT_TRAINING_WARNING)

        return items


orchestration_service = OrchestrationService()
