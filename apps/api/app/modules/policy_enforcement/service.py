import re

from app.modules.contracts import codes
from app.modules.policy_enforcement.schemas import PolicyEnforcementResult
from app.modules.project_context.schemas import ProjectContext, TaskPolicyResult
from app.modules.project_context.service import (
    ELYRA_ORIGIN_SYSTEMS,
    FINGUARD_ORIGIN_SYSTEMS,
    UNKNOWN_PROJECT_ID,
)
from app.modules.task_router.schemas import TaskStrategy

# Enforcement forte de policy (IMPLEMENT-05B + FINALIZE-06A).
#
# Diferente da policy informativa (TaskPolicyResult, que só gera warning),
# este módulo BLOQUEIA de verdade:
#   - task_type com semântica perigosa (executar/escrever/deletar/migrar/deploy);
#   - payload com instruções de execução de comando em metadata/context;
#   - task não permitida para o projeto quando o fluxo é crítico;
#   - origem desconhecida em fluxo crítico.
# O enforcement é controlado por PEDROCORE_ENFORCE_PROJECT_POLICY (default true).

_DANGEROUS_TASK_WORDS = re.compile(
    r"\b(execute|exec|command|comando|write|escrever|escreva|delete|deletar|"
    r"drop|truncate|migrate|migration|migrar|push|commit|deploy|destroy|"
    r"apagar|reset|shutdown|kill)\b",
    re.IGNORECASE,
)

DANGEROUS_PAYLOAD_KEYS = {
    "command",
    "commands",
    "cmd",
    "exec",
    "execute",
    "shell",
    "script",
    "run_command",
    "write_file",
    "delete",
}

DANGEROUS_TASK_REASON = (
    "task_type com semântica de execução/escrita/deleção é bloqueado por policy; "
    "o Veltrix não executa comandos, não escreve e não deleta."
)

DANGEROUS_PAYLOAD_REASON = (
    "Payload contém instruções de execução de comando (metadata/context); "
    "bloqueado por policy."
)

CRITICAL_TASK_NOT_ALLOWED_REASON = (
    "task_type não permitido para o projeto em fluxo crítico; bloqueado por policy."
)

UNKNOWN_ORIGIN_CRITICAL_REASON = (
    "Origem desconhecida não pode executar fluxo crítico; bloqueado por policy."
)


def _keys_of(data: dict | None) -> set[str]:
    if not data:
        return set()
    return {str(key).strip().lower() for key in data}


class PolicyEnforcementService:
    def evaluate(
        self,
        raw_task_type: str | None,
        strategy: TaskStrategy,
        project: ProjectContext,
        policy: TaskPolicyResult,
        metadata: dict | None = None,
        context: dict | None = None,
        enforce: bool = True,
    ) -> PolicyEnforcementResult:
        raw = (raw_task_type or "").strip().lower().replace("_", " ").replace("-", " ")

        if raw and _DANGEROUS_TASK_WORDS.search(raw):
            reason = DANGEROUS_TASK_REASON
            if project.project_id in FINGUARD_ORIGIN_SYSTEMS:
                reason = (
                    "FinGuard é read-only no Veltrix: " + DANGEROUS_TASK_REASON
                )
            return PolicyEnforcementResult(
                blocked=True,
                error_code=codes.PROJECT_POLICY_BLOCKED,
                blocked_reason=reason,
                warnings=[reason],
                warning_codes=[codes.PROJECT_POLICY_BLOCKED],
            )

        payload_keys = _keys_of(metadata) | _keys_of(context)
        if payload_keys & DANGEROUS_PAYLOAD_KEYS:
            return PolicyEnforcementResult(
                blocked=True,
                error_code=codes.PROJECT_POLICY_BLOCKED,
                blocked_reason=DANGEROUS_PAYLOAD_REASON,
                warnings=[DANGEROUS_PAYLOAD_REASON],
                warning_codes=[codes.PROJECT_POLICY_BLOCKED],
            )

        if not enforce:
            return PolicyEnforcementResult()

        is_critical_flow = strategy.criticality in {"high", "critical"}

        # Elyra opera fail-closed para QUALQUER task: allowed_tasks é o
        # mecanismo nativo de capabilities. Multimodal/learning só existirão
        # quando forem adicionados explicitamente em futuras frentes.
        if project.project_id in ELYRA_ORIGIN_SYSTEMS and not policy.allowed:
            return PolicyEnforcementResult(
                blocked=True,
                error_code=codes.PROJECT_POLICY_BLOCKED,
                blocked_reason=CRITICAL_TASK_NOT_ALLOWED_REASON,
                warnings=[CRITICAL_TASK_NOT_ALLOWED_REASON],
                warning_codes=[codes.PROJECT_POLICY_BLOCKED],
            )

        if is_critical_flow and not policy.allowed:
            code = (
                codes.FINGUARD_TASK_NOT_ALLOWED
                if project.project_id in FINGUARD_ORIGIN_SYSTEMS
                else codes.PROJECT_POLICY_BLOCKED
            )
            return PolicyEnforcementResult(
                blocked=True,
                error_code=code,
                blocked_reason=CRITICAL_TASK_NOT_ALLOWED_REASON,
                warnings=[CRITICAL_TASK_NOT_ALLOWED_REASON],
                warning_codes=[code],
            )

        if is_critical_flow and project.project_id == UNKNOWN_PROJECT_ID:
            return PolicyEnforcementResult(
                blocked=True,
                error_code=codes.PROJECT_POLICY_BLOCKED,
                blocked_reason=UNKNOWN_ORIGIN_CRITICAL_REASON,
                warnings=[UNKNOWN_ORIGIN_CRITICAL_REASON],
                warning_codes=[codes.PROJECT_POLICY_BLOCKED],
            )

        return PolicyEnforcementResult()


policy_enforcement_service = PolicyEnforcementService()
