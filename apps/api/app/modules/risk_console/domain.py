"""Traducao entre o que o humano escolhe e o que o core entende.

O console apresenta rotulos em portugues; o motor trabalha com valores
canonicos. A traducao mora aqui e em nenhum outro lugar, para que a tela nunca
invente um valor que o motor nao reconhece — e para que o rename futuro nao
precise mexer em regra de negocio.

Nada aqui decide risco. Isto e montagem de requisicao.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.modules.project_context.manifests import PROJECT_MANIFESTS
from app.modules.risk_console.branding import CONSOLE_AGENT_ID, CONSOLE_PRODUCER
from app.modules.risk_engine.analyzers import infer_operation_kind
from app.modules.risk_engine.schemas import (
    OperationKind,
    RequestedOperation,
    RiskContextInput,
    RiskRequest,
)
from app.modules.universal_contracts.capability_manifest import ProjectCapability

# --- ambientes ------------------------------------------------------------
#
# Rotulo humano -> valor canonico ja usado pelo motor. `production` importa:
# as regras deterministicas comparam com {"prod", "production"} para decidir
# BLOCK de segredo em producao.

ENVIRONMENTS: tuple[tuple[str, str], ...] = (
    ("Desenvolvimento", "development"),
    ("Teste", "test"),
    ("Produção", "production"),
)

# --- executores -----------------------------------------------------------
#
# Nesta frente o executor e CONTEXTO, nao acao: o console registra quem
# executaria e nao invoca agente algum. `agent_id` viaja para o motor e para o
# contrato, entao a escolha muda a analise — mas nunca dispara execucao.

EXECUTORS: tuple[tuple[str, str], ...] = (
    ("Claude Code", "claude-code"),
    ("Codex", "codex"),
    ("Agente genérico", "generic-agent"),
    ("Manual", "manual"),
)

# --- operacoes ------------------------------------------------------------

OPERATIONS: tuple[tuple[str, OperationKind], ...] = (
    ("Ler / auditar", OperationKind.READ),
    ("Escrever / alterar", OperationKind.WRITE),
    ("Excluir", OperationKind.DELETE),
    ("Migrar banco", OperationKind.MIGRATE),
    ("Publicar / deploy", OperationKind.DEPLOY),
    ("Configurar", OperationKind.CONFIGURE),
    ("Executar comando", OperationKind.EXECUTE),
    ("Não declarada", OperationKind.UNKNOWN),
)

_ENVIRONMENT_BY_LABEL = {label: value for label, value in ENVIRONMENTS}
_ENVIRONMENT_BY_VALUE = {value: label for label, value in ENVIRONMENTS}
_EXECUTOR_BY_LABEL = {label: value for label, value in EXECUTORS}
_EXECUTOR_BY_VALUE = {value: label for label, value in EXECUTORS}
_OPERATION_BY_VALUE = {kind.value: label for label, kind in OPERATIONS}
_OPERATION_BY_LABEL = {label: kind for label, kind in OPERATIONS}


class ConsoleInputError(ValueError):
    """Entrada recusada antes de chegar ao motor, com mensagem em PT-BR."""


def available_projects() -> tuple[str, ...]:
    """Projetos que DECLARAM a capability de analise de risco.

    Derivado do Capability Manifest, nunca de uma lista fixa no console. Um
    projeto novo aparece aqui por declarar o que faz — e o console continua
    sem saber o nome de nenhum projeto em particular.
    """
    return tuple(
        sorted(
            project_id
            for project_id, manifest in PROJECT_MANIFESTS.items()
            if manifest.declares(ProjectCapability.RISK_ANALYSIS)
        )
    )


def environment_value(label: str) -> str:
    try:
        return _ENVIRONMENT_BY_LABEL[label]
    except KeyError:
        raise ConsoleInputError(
            f"Ambiente inválido: {label!r}. Use um de: "
            + ", ".join(item for item, _ in ENVIRONMENTS)
        ) from None


def environment_label(value: str) -> str:
    return _ENVIRONMENT_BY_VALUE.get(value, value)


def executor_value(label: str) -> str:
    try:
        return _EXECUTOR_BY_LABEL[label]
    except KeyError:
        raise ConsoleInputError(
            f"Executor inválido: {label!r}. Use um de: "
            + ", ".join(item for item, _ in EXECUTORS)
        ) from None


def executor_label(value: str) -> str:
    return _EXECUTOR_BY_VALUE.get(value, value)


def operation_label(kind: OperationKind | str) -> str:
    value = kind.value if isinstance(kind, OperationKind) else str(kind)
    return _OPERATION_BY_VALUE.get(value, value)


def operation_from_label(label: str) -> OperationKind:
    try:
        return _OPERATION_BY_LABEL[label]
    except KeyError:
        raise ConsoleInputError(f"Operação inválida: {label!r}.") from None


def split_list(raw: str) -> list[str]:
    """Campo de texto para lista. Vírgula ou quebra de linha separam."""
    parts: list[str] = []
    for chunk in (raw or "").replace("\n", ",").split(","):
        item = chunk.strip()
        if item:
            parts.append(item)
    return parts


@dataclass(slots=True)
class ConsoleRequestInput:
    """O que o humano preencheu, ainda em rotulos de interface."""

    project_id: str
    environment_label: str
    executor_label: str
    prompt: str
    operation: OperationKind | None = None
    permissions: list[str] = field(default_factory=list)
    allowed_scope: list[str] = field(default_factory=list)
    forbidden_scope: list[str] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)
    required_tests: list[str] = field(default_factory=list)
    external_integrations: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    database: str | None = None
    rollback_plan_present: bool = False
    request_id: str | None = None


def prompt_limit() -> int:
    """Limite real de `request_text` no contrato V1, lido do proprio schema."""
    for item in RiskRequest.model_fields["request_text"].metadata:
        limit = getattr(item, "max_length", None)
        if limit is not None:
            return int(limit)
    raise RuntimeError("RiskRequest.request_text sem max_length declarado")


def build_request(entry: ConsoleRequestInput) -> RiskRequest:
    """Monta o `RiskRequest` V1 que o motor ja entende.

    O console NAO inventa contexto para melhorar o resultado. Se o usuario nao
    declarou permissao nem escopo, a requisicao vai sem eles e o motor
    responde o que tem de responder — normalmente BLOCK por
    `PERMISSION_CONFLICT`. Preencher permissao silenciosamente para produzir
    um PASS transformaria o console num falsificador de aprovacao.
    """
    prompt = (entry.prompt or "").strip()
    if not prompt:
        raise ConsoleInputError("Prompt vazio: descreva a operação a ser analisada.")

    projects = available_projects()
    project_id = (entry.project_id or "").strip().lower()
    if project_id not in projects:
        raise ConsoleInputError(
            f"Projeto {entry.project_id!r} não declara a capability 'risk_analysis'. "
            "Projetos disponíveis: " + (", ".join(projects) or "nenhum")
        )

    environment = environment_value(entry.environment_label)
    executor = executor_value(entry.executor_label)
    operation = entry.operation or infer_operation_kind(prompt)

    # O limite e do motor. Cortar em silencio mudaria o que foi analisado sem
    # o usuario saber que mudou.
    limit = prompt_limit()
    if len(prompt) > limit:
        raise ConsoleInputError(
            f"Prompt com {len(prompt)} caracteres excede o limite de {limit} do Risk Engine."
        )

    return RiskRequest(
        request_id=entry.request_id or f"console-{uuid.uuid4().hex[:16]}",
        producer=CONSOLE_PRODUCER,
        project_id=project_id,
        request_text=prompt,
        environment=environment,
        agent_id=f"{CONSOLE_AGENT_ID}:{executor}",
        permissions=entry.permissions,
        context=RiskContextInput(
            allowed_scope=entry.allowed_scope,
            forbidden_scope=entry.forbidden_scope,
            known_modules=[],
            constraints=entry.constraints,
            acceptance_criteria=entry.acceptance_criteria,
            database=entry.database,
            external_integrations=entry.external_integrations,
            required_tests=entry.required_tests,
            rollback_plan_present=entry.rollback_plan_present,
        ),
        requested_operation=RequestedOperation(
            kind=operation,
            targets=entry.targets,
            expected_changes=[],
            commands=[],
            destructive=operation is OperationKind.DELETE,
            external_effects=bool(entry.external_integrations),
        ),
    )
