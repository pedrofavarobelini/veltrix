from __future__ import annotations

from app.modules.risk_engine.schemas import (
    AmbiguityAnalysis,
    ExecutionIntent,
    OperationKind,
    PromptQuality,
    ResolvedContext,
    RiskRequest,
    ScopeAnalysis,
)

_OPERATION_TERMS: tuple[tuple[OperationKind, tuple[str, ...]], ...] = (
    (OperationKind.DELETE, ("delete", "remove", "drop", "excluir", "apagar")),
    (OperationKind.MIGRATE, ("migrate", "migration", "migrar", "migração")),
    (OperationKind.DEPLOY, ("deploy", "release", "publicar", "produção")),
    (OperationKind.CONFIGURE, ("configure", "config", ".env", "configurar")),
    (OperationKind.WRITE, ("write", "change", "edit", "alterar", "modificar")),
    (OperationKind.EXECUTE, ("execute", "run", "executar", "rodar")),
    (OperationKind.READ, ("read", "inspect", "audit", "ler", "auditar")),
)
_MUTATING = {
    OperationKind.WRITE,
    OperationKind.DELETE,
    OperationKind.MIGRATE,
    OperationKind.DEPLOY,
    OperationKind.CONFIGURE,
    OperationKind.EXECUTE,
}


def _unique(values: list[str]) -> list[str]:
    return sorted({item.strip() for item in values if item.strip()}, key=str.lower)


def infer_operation_kind(text: str) -> OperationKind:
    """Infere a operacao a partir do texto livre.

    Extraido de `IntentAnalyzer` sem mudanca de comportamento para que o Risk
    Console possa PRE-PREENCHER a operacao usando exatamente a mesma tabela de
    termos que o motor usa. Duas tabelas divergiriam com o tempo, e o console
    passaria a sugerir uma operacao que o motor nao reconhece.

    O console mostra o resultado como inferido e deixa o humano corrigir: quem
    declara a operacao continua sendo o consumidor, nao o texto.
    """
    lowered = text.lower()
    for operation, terms in _OPERATION_TERMS:
        if any(term in lowered for term in terms):
            return operation
    return OperationKind.UNKNOWN


class IntentAnalyzer:
    def analyze(self, request: RiskRequest) -> ExecutionIntent:
        inferred = infer_operation_kind(request.request_text)
        explicit = request.requested_operation.kind is not OperationKind.UNKNOWN
        consistent = inferred in {OperationKind.UNKNOWN, request.requested_operation.kind}
        operation = request.requested_operation.kind
        return ExecutionIntent(
            operation=operation,
            inferred_operation=inferred,
            targets=_unique(request.requested_operation.targets),
            mutating=operation in _MUTATING,
            destructive=(
                request.requested_operation.destructive or operation is OperationKind.DELETE
            ),
            external_effects=request.requested_operation.external_effects,
            explicit_intent=explicit,
            intent_consistent=consistent,
        )


class ContextResolver:
    def resolve(self, request: RiskRequest) -> ResolvedContext:
        context = request.context
        missing: list[str] = []
        if not request.permissions:
            missing.append("permissions")
        if not context.allowed_scope:
            missing.append("allowed_scope")
        if request.requested_operation.kind is OperationKind.MIGRATE and not context.database:
            missing.append("database")
        if request.requested_operation.external_effects and not context.external_integrations:
            missing.append("external_integrations")
        return ResolvedContext(
            project_id=request.project_id.strip().lower(),
            environment=request.environment.strip().lower(),
            agent_id=request.agent_id.strip(),
            permissions=_unique(request.permissions),
            allowed_scope=_unique(context.allowed_scope),
            forbidden_scope=_unique(context.forbidden_scope),
            known_files=_unique(context.known_files),
            known_modules=_unique(context.known_modules),
            database=context.database,
            user_scope=context.user_scope,
            external_integrations=_unique(context.external_integrations),
            constraints=_unique(context.constraints),
            acceptance_criteria=_unique(context.acceptance_criteria),
            required_tests=_unique(context.required_tests),
            rollback_plan_present=context.rollback_plan_present,
            missing_context=missing,
        )


class PromptQualityAnalyzer:
    def analyze(self, intent: ExecutionIntent, context: ResolvedContext) -> PromptQuality:
        checks = {
            "has_explicit_operation": intent.explicit_intent,
            "has_targets": bool(intent.targets),
            "has_constraints": bool(context.constraints),
            "has_acceptance_criteria": bool(context.acceptance_criteria),
            "has_tests": bool(context.required_tests),
            "has_rollback": context.rollback_plan_present or not intent.mutating,
        }
        reasons = [key.upper() + "_MISSING" for key, present in checks.items() if not present]
        return PromptQuality(
            score=round(sum(checks.values()) / len(checks), 6),
            reason_codes=reasons,
            **checks,
        )


class AmbiguityDetector:
    def analyze(
        self,
        intent: ExecutionIntent,
        context: ResolvedContext,
    ) -> AmbiguityAnalysis:
        codes: list[str] = []
        if not intent.explicit_intent:
            codes.append("OPERATION_UNKNOWN")
        if not intent.targets:
            codes.append("TARGETS_MISSING")
        if not intent.intent_consistent:
            codes.append("TEXT_OPERATION_CONFLICT")
        if context.missing_context:
            codes.append("CONTEXT_INCOMPLETE")
        return AmbiguityAnalysis(ambiguous=bool(codes), ambiguity_codes=codes)


class ScopeAnalyzer:
    def analyze(self, intent: ExecutionIntent, context: ResolvedContext) -> ScopeAnalysis:
        allowed = set(context.allowed_scope)
        forbidden = set(context.forbidden_scope)
        targets = set(intent.targets)
        forbidden_targets = sorted(targets & forbidden)
        in_scope = sorted(targets & allowed)
        outside = sorted(targets - allowed) if allowed else []
        unknown = sorted(targets) if not allowed else []
        return ScopeAnalysis(
            bounded=bool(targets) and not outside and not forbidden_targets and not unknown,
            targets_in_scope=in_scope,
            targets_outside_scope=outside,
            forbidden_targets=forbidden_targets,
            unknown_targets=unknown,
        )
