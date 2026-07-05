import time

from app.core.config import settings
from app.modules.artifact_reader.service import artifact_reader_service
from app.modules.artifacts.schemas import ArtifactInput, ArtifactProcessingResult
from app.modules.artifacts.service import PATH_LIKE_METADATA_KEYS, artifact_service
from app.modules.audit.service import audit_service
from app.modules.chat.schemas import ChatRequest
from app.modules.contracts import codes
from app.modules.contracts.codes import WarningItem, make_warning
from app.modules.exploration.service import exploration_service
from app.modules.orchestration.schemas import OrchestrationOutcome
from app.modules.policy_enforcement.service import policy_enforcement_service
from app.modules.real_features import service as real_features
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

PROVIDER_REAL_BLOCKED_WARNING = (
    "Provider real bloqueado pelo safe mode (allow_real_provider=false); "
    "fallback seguro aplicado."
)

READER_FINGUARD_ORIGIN_WARNING = (
    "Artifact Reader não está disponível para origem FinGuard nesta frente; "
    "artefatos devem ser enviados por payload."
)

VISUAL_ONLY_RELEASE_GATE_WARNING = (
    "Release gate não pode ser liberado apenas com evidência visual não analisada; "
    "envie evidência textual."
)


class OrchestrationService:
    """Pipeline central: Task Router → Project Context → Policy → Artifacts →
    Provider (com safe mode) → QA Text Analyzer local → QA Response/Release Gate → Audit."""

    async def execute(self, payload: ChatRequest) -> OrchestrationOutcome:
        started = time.perf_counter()

        strategy = task_router.resolve(payload.task_type)
        project = project_context_resolver.resolve(payload.origin_system)
        policy = project_context_resolver.evaluate_task_policy(project, strategy.task_type)
        requested_provider = (payload.provider or settings.default_provider).lower()

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
                started=started,
            )

        effective_artifacts, reader_items = self._apply_artifact_reader(payload)
        artifacts_result = artifact_service.process(effective_artifacts)

        audit = audit_service.create(
            origin_system=payload.origin_system,
            task_type=strategy.task_type,
            provider_requested=requested_provider,
            criticality=strategy.criticality,
        )

        prompt = prompt_builder.build(
            PromptBuildInput(
                message=payload.message,
                mode=payload.mode,
                system_prompt=payload.system_prompt,
                strategy=strategy,
                project=project,
                origin_system=payload.origin_system,
                context=payload.context,
                metadata=payload.metadata,
                artifacts_text_block=artifacts_result.text_block,
            )
        )

        fallback_used = False
        safe_mode_blocked = False
        error: str | None = None
        error_code: str | None = None

        if requested_provider in LOCAL_PROVIDERS:
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

            if provider is None:
                error = f"Provider não suportado: {requested_provider}"
                answer, provider_used, model_used = await self._mock_fallback(
                    payload, requested_provider, error, prompt.enriched_system_prompt
                )
                fallback_used = True
            elif provider.real_provider and not payload.allow_real_provider:
                safe_mode_blocked = True
                error = PROVIDER_REAL_BLOCKED_WARNING
                error_code = codes.PROVIDER_REAL_BLOCKED
                answer, provider_used, model_used = await self._mock_fallback(
                    payload, requested_provider, error, prompt.enriched_system_prompt
                )
                fallback_used = True
            else:
                try:
                    result = await provider.generate_response(
                        message=payload.message,
                        mode=payload.mode,
                        model=payload.model,
                        system_prompt=prompt.enriched_system_prompt,
                    )
                    answer = result.answer
                    provider_used = result.provider
                    model_used = result.model
                except Exception as exc:
                    error = str(exc)
                    answer, provider_used, model_used = await self._mock_fallback(
                        payload, requested_provider, error, prompt.enriched_system_prompt
                    )
                    fallback_used = True

            analysis = qa_text_analyzer.analyze(
                task_type=strategy.task_type,
                artifacts_result=artifacts_result,
                fallback_used=fallback_used,
                safe_mode_blocked=safe_mode_blocked,
            )

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
        )

        blocked_reason: str | None = None
        if release_gate is not None and not release_gate.can_advance:
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

    def _policy_blocked_outcome(
        self,
        payload: ChatRequest,
        strategy,
        project,
        policy,
        enforcement,
        requested_provider: str,
        started: float,
    ) -> OrchestrationOutcome:
        """Bloqueio real por policy: nenhum provider, reader ou análise é executado."""
        audit = audit_service.create(
            origin_system=payload.origin_system,
            task_type=strategy.task_type,
            provider_requested=requested_provider,
            criticality=strategy.criticality,
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
            "Solicitação bloqueada por policy do PedroCore. "
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
        )

    async def _mock_fallback(
        self,
        payload: ChatRequest,
        requested_provider: str,
        error: str,
        enriched_system_prompt: str,
    ) -> tuple[str, str, str]:
        mock = provider_registry.mock()
        fallback_message = (
            f"Fallback acionado. O provider '{requested_provider}' falhou, não está "
            f"configurado ou foi bloqueado.\n\n"
            f"Erro técnico: {error}\n\n"
            f"Mensagem original: {payload.message}"
        )
        result = await mock.generate_response(
            message=fallback_message,
            mode=payload.mode,
            model="mock-v1",
            system_prompt=enriched_system_prompt,
        )
        return result.answer, "mock", "mock-v1"

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

        return items


orchestration_service = OrchestrationService()
