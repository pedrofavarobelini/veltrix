"""Apresentacao: rotulos em PT-BR e derivacoes a partir de fatos reais.

Fronteira deste modulo
----------------------

Ele TRADUZ e ORGANIZA. Ele nao decide.

O gate vem do core (`execution_contract_service.gate_for`) e aqui so ganha um
rotulo em portugues. O enum interno nao muda: traduzir contrato para acomodar
interface e como renomear a lei para caber no cartaz.

As recomendacoes sao DERIVADAS de campos que a analise ja produziu — nunca
inventadas para preencher espaco. Se a analise nao trouxe o fato, a
recomendacao correspondente nao aparece. Uma recomendacao sem fato por tras
seria conselho de adivinho com aparencia de laudo.

Elas tambem NAO influenciam o gate: sao lidas depois que a decisao ja foi
tomada pelo core, e nada aqui volta para o motor.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.risk_console.branding import (
    COLOR_ACCENT,
    COLOR_CRITICAL,
    COLOR_DANGER,
    COLOR_MUTED,
    COLOR_OK,
    COLOR_WARN,
)
from app.modules.risk_engine.execution_contract_schemas import RiskGate
from app.modules.risk_engine.pre_execution_schemas import (
    PreExecutionRiskAnalysis,
    RiskDimensionName,
)
from app.modules.risk_engine.schemas import RiskSeverity

# --- gates ----------------------------------------------------------------
#
# Interno preservado; apresentacao traduzida.

GATE_LABELS: dict[RiskGate, str] = {
    RiskGate.PASS: "APROVADO",
    RiskGate.PASS_WITH_WARNINGS: "APROVADO COM AVISOS",
    RiskGate.REVIEW_REQUIRED: "REVISÃO OBRIGATÓRIA",
    RiskGate.BLOCK: "BLOQUEADO",
}

GATE_COLORS: dict[RiskGate, str] = {
    RiskGate.PASS: COLOR_OK,
    RiskGate.PASS_WITH_WARNINGS: COLOR_WARN,
    RiskGate.REVIEW_REQUIRED: COLOR_WARN,
    RiskGate.BLOCK: COLOR_DANGER,
}

SEVERITY_LABELS: dict[RiskSeverity, str] = {
    RiskSeverity.INFO: "INFORMATIVO",
    RiskSeverity.LOW: "BAIXO",
    RiskSeverity.MEDIUM: "MÉDIO",
    RiskSeverity.HIGH: "ALTO",
    RiskSeverity.CRITICAL: "CRÍTICO",
}

SEVERITY_COLORS: dict[RiskSeverity, str] = {
    RiskSeverity.INFO: COLOR_MUTED,
    RiskSeverity.LOW: COLOR_OK,
    RiskSeverity.MEDIUM: COLOR_WARN,
    RiskSeverity.HIGH: COLOR_DANGER,
    RiskSeverity.CRITICAL: COLOR_CRITICAL,
}

DIMENSION_LABELS: dict[RiskDimensionName, str] = {
    RiskDimensionName.SCOPE: "Escopo",
    RiskDimensionName.REGRESSION: "Regressão",
    RiskDimensionName.DATA: "Dados",
    RiskDimensionName.SECURITY: "Segurança",
    RiskDimensionName.MIGRATION: "Migração",
    RiskDimensionName.OPERATIONAL: "Operacional",
}

ROLLBACK_LABELS: dict[str, str] = {
    "none": "não exigido",
    "recommended": "recomendado",
    "required": "obrigatório",
}

# Cenarios emitidos pelo motor. Rotulo humano para cada um; um cenario novo
# que nao esteja aqui aparece com o proprio identificador, nunca escondido.
SCENARIO_LABELS: dict[str, str] = {
    "success": "Sucesso",
    "partial_failure": "Falha parcial",
    "scope_deviation": "Desvio de escopo",
    "dependency_failure": "Falha de dependência",
    "rollback_requirement": "Necessidade de rollback",
    "security_impact": "Impacto de segurança",
    "data_corruption": "Corrupção de dados",
    "migration_failure": "Falha de migração",
    "test_failure": "Falha de teste exigido",
    "external_service_failure": "Falha de serviço externo",
}

# Motivos de gate que o core emite. Traduzidos para que o usuario entenda o
# porque sem precisar ler o codigo da politica.
REASON_LABELS: dict[str, str] = {
    "FORBIDDEN_SCOPE": "Alvo dentro de escopo proibido declarado.",
    "PERMISSION_CONFLICT": "Permissão necessária para a operação não foi declarada.",
    "OPERATION_UNKNOWN": "Operação não declarada e não inferível do prompt.",
    "PRODUCTION_SECRET_CHANGE": "Alteração de segredo/configuração em produção.",
    "CRITICAL_CONTEXT_MISSING": "Contexto essencial ausente na requisição.",
    "HIGH_RISK_REVIEW": "Sinais de risco alto ou crítico exigem revisão humana.",
    "HISTORICAL_RISK_REVIEW": "Histórico do projeto registra padrão de risco semelhante.",
    "NON_BLOCKING_RISK_SIGNALS": "Sinais de risco presentes, nenhum bloqueante.",
    "POLICY_REQUIREMENTS_SATISFIED": "Requisitos da política satisfeitos.",
}

CONTEXT_LABELS: dict[str, str] = {
    "permissions": "permissões",
    "allowed_scope": "escopo permitido",
    "database": "banco de dados",
    "external_integrations": "integrações externas",
}


def gate_label(gate: RiskGate) -> str:
    return GATE_LABELS[gate]


def gate_color(gate: RiskGate) -> str:
    return GATE_COLORS[gate]


def severity_label(severity: RiskSeverity | None) -> str:
    return SEVERITY_LABELS[severity] if severity is not None else "—"


def severity_color(severity: RiskSeverity | None) -> str:
    return SEVERITY_COLORS[severity] if severity is not None else COLOR_MUTED


def scenario_label(scenario: str) -> str:
    return SCENARIO_LABELS.get(scenario, scenario)


def dimension_label(dimension: RiskDimensionName) -> str:
    return DIMENSION_LABELS.get(dimension, dimension.value)


def reason_label(code: str) -> str:
    return REASON_LABELS.get(code, code)


def rollback_label(value: str) -> str:
    return ROLLBACK_LABELS.get(value, value)


def percent(value: float) -> str:
    return f"{round(value * 100)}%"


def quality_label(score: float) -> str:
    """Qualidade do prompt em escala de 100, como o usuário lê."""
    return f"{round(score * 100)}/100"


def ambiguity_label(ambiguous: bool) -> str:
    return "ALTA" if ambiguous else "BAIXA"


def accent() -> str:
    return COLOR_ACCENT


@dataclass(frozen=True, slots=True)
class Recommendation:
    """Uma acao concreta, com o fato que a originou.

    `basis` existe para que nenhuma recomendacao seja opaca: quem lê pode
    conferir de onde ela saiu.
    """

    text: str
    basis: str


def derive_recommendations(
    analysis: PreExecutionRiskAnalysis,
    gate: RiskGate,
    gate_reasons: list[str],
) -> list[Recommendation]:
    """Recomendacoes derivadas SOMENTE de fatos ja presentes na analise.

    Cada ramo abaixo depende de um campo real. Sem o campo, sem a
    recomendacao — e por isso uma analise limpa produz uma lista curta, que e
    a resposta honesta em vez de uma lista longa de conselhos genericos.
    """
    items: list[Recommendation] = []

    missing = analysis.foundation.resolved_context.missing_context
    if missing:
        legivel = ", ".join(CONTEXT_LABELS.get(str(item), str(item)) for item in missing)
        items.append(
            Recommendation(
                text=f"Declare o contexto ausente antes de executar: {legivel}.",
                basis="resolved_context.missing_context",
            )
        )

    if "PERMISSION_CONFLICT" in gate_reasons:
        items.append(
            Recommendation(
                text=(
                    "Declare a permissão correspondente à operação "
                    "(ex.: 'write:<módulo>' para escrita)."
                ),
                basis="gate: PERMISSION_CONFLICT",
            )
        )

    forbidden = analysis.foundation.scope.forbidden_targets
    if forbidden:
        items.append(
            Recommendation(
                text=(
                    "Remova do pedido os alvos em escopo proibido: "
                    + ", ".join(forbidden)
                ),
                basis="scope.forbidden_targets",
            )
        )

    outside = analysis.foundation.scope.targets_outside_scope
    if outside:
        items.append(
            Recommendation(
                text=(
                    "Inclua no escopo permitido, ou retire do pedido, os alvos: "
                    + ", ".join(outside)
                ),
                basis="scope.targets_outside_scope",
            )
        )

    if analysis.foundation.ambiguity.ambiguous:
        items.append(
            Recommendation(
                text=(
                    "Reescreva o prompt delimitando alvo e resultado esperado: "
                    "o texto atual admite mais de uma interpretação."
                ),
                basis="ambiguity.ambiguous",
            )
        )

    quality = analysis.foundation.prompt_quality
    if not quality.has_acceptance_criteria:
        items.append(
            Recommendation(
                text="Declare critérios de aceitação para que o resultado seja verificável.",
                basis="prompt_quality.has_acceptance_criteria",
            )
        )
    if not quality.has_tests:
        items.append(
            Recommendation(
                text="Declare os testes exigidos antes de promover a mudança.",
                basis="prompt_quality.has_tests",
            )
        )

    if any(item.rollback_requirement == "required" for item in analysis.simulations):
        if not analysis.foundation.resolved_context.rollback_plan_present:
            items.append(
                Recommendation(
                    text=(
                        "Prepare e declare um plano de rollback: há cenário que o "
                        "exige como obrigatório."
                    ),
                    basis="simulations[].rollback_requirement=required",
                )
            )

    if gate is RiskGate.BLOCK:
        items.append(
            Recommendation(
                text=(
                    "Corrija os motivos do bloqueio e execute nova análise. "
                    "A execução não deve ser tentada neste estado."
                ),
                basis="gate: BLOCK",
            )
        )
    elif gate is RiskGate.REVIEW_REQUIRED:
        items.append(
            Recommendation(
                text="Obtenha revisão humana registrada antes de executar.",
                basis="gate: REVIEW_REQUIRED",
            )
        )

    return items


# Regras deterministicas: frase humana por regra.
#
# O motor descreve o achado como "Regra determinística acionada:
# database_migration." — util para auditoria, ruim para leitura. O usuario
# precisa saber O QUE foi detectado antes de saber COMO a regra se chama.
#
# O identificador continua existindo e vive em DETALHES TÉCNICOS.
RULE_EXPLANATIONS: dict[str, str] = {
    "database_migration": "O pedido envolve migração de banco de dados.",
    "schema_change": "O pedido altera o schema do banco.",
    "auth_authz": "O pedido toca autenticação ou autorização.",
    "secrets_env": "O pedido menciona segredo, credencial ou variável de ambiente.",
    "ci_cd": "O pedido altera pipeline de integração ou entrega.",
    "delete": "O pedido remove ou apaga dados.",
    "mass_file_change": "O pedido altera arquivos em massa.",
    "security_policy": "O pedido altera política de segurança ou acesso.",
    "production_config": "O pedido envolve configuração de produção.",
    "permissions": "O pedido altera permissões ou papéis.",
    "external_integration": "O pedido envolve integração externa.",
}

_RULE_PREFIX = "Regra determinística acionada: "


def humanize_finding(title: str) -> str:
    """Frase humana para um achado, quando ele for o eco de uma regra.

    Achado que nao vem de regra ja e texto humano e passa intacto: reescrever
    o que ja esta bom seria trocar a voz do motor pela minha.
    """
    if not title.startswith(_RULE_PREFIX):
        return title
    identificador = title[len(_RULE_PREFIX) :].rstrip(".").strip()
    return RULE_EXPLANATIONS.get(identificador, title)
