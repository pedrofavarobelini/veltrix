"""Exportacao sanitizada da analise.

Por que sanitizar na saida
--------------------------

O prompt e digitado por um humano com pressa. Um dia ele vai colar uma string
de conexao ou um token dentro do texto para "dar contexto". A analise em si
nao guarda segredo, mas o prompt viaja junto com ela — e um arquivo exportado
costuma acabar num anexo, num chat ou num ticket.

Por isso a redacao acontece na fronteira de saida, e nao na entrada: o motor
precisa analisar o texto como ele e, e quem sai do processo e que precisa
estar limpo.

A redacao e conservadora por escolha. Ela prefere marcar demais a deixar
passar: um `[REDIGIDO]` a mais custa uma pergunta, um token a menos custa uma
rotacao de credencial.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from app.modules.risk_console.analysis import ConsoleAnalysis
from app.modules.risk_console.branding import PRODUCT_NAME
from app.modules.risk_console.presentation import (
    dimension_label,
    gate_label,
    reason_label,
    rollback_label,
    scenario_label,
    severity_label,
)

REDACTED = "[REDIGIDO]"

# Cada padrao corresponde a uma forma concreta de segredo em texto livre.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    # chave=valor, com nome que denuncia o conteudo
    re.compile(
        r"(?i)\b(api[_-]?key|apikey|secret|password|senha|token|bearer|authorization)"
        r"\s*[:=]\s*\S+"
    ),
    # strings de conexao com credencial embutida
    re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s/@]+@\S+"),
    # prefixos de token conhecidos
    re.compile(r"\b(sk|pk|ghp|gho|ghs|xox[baprs])[-_][A-Za-z0-9_-]{16,}\b"),
    # blocos PEM
    re.compile(r"-----BEGIN[^-]{0,40}PRIVATE KEY-----[\s\S]*?-----END[^-]{0,40}KEY-----"),
)


def redact(text: str) -> str:
    """Substitui trechos com cara de segredo, preservando o resto do texto."""
    cleaned = text or ""
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub(REDACTED, cleaned)
    return cleaned


def as_dict(result: ConsoleAnalysis) -> dict:
    """Estrutura exportavel: fatos reais da analise, prompt redigido.

    Nao inclui `permissions` nem string de ambiente crua alem do necessario, e
    nao inclui nenhum objeto do processo — apenas o que ja e contrato publico
    do Risk Engine, mais os rotulos que a interface mostrou.
    """
    analysis = result.analysis
    foundation = analysis.foundation
    radius = analysis.blast_radius
    metric = radius.metric

    return {
        "produto": PRODUCT_NAME,
        "exportado_em": datetime.now(timezone.utc).isoformat(),
        "analise_id": analysis.analysis_id,
        "requisicao_id": analysis.request_id,
        "projeto": analysis.project_id,
        "ambiente": result.request.environment,
        "executor": result.request.agent_id,
        "politica": analysis.policy_version,
        "prompt": redact(result.request.request_text),
        "operacao_alvo_executada": analysis.target_operation_executed,
        "provider_chamado": analysis.provider_called,
        "intencao": {
            "operacao": foundation.intent.operation.value,
            "operacao_inferida": foundation.intent.inferred_operation.value,
            "modifica": foundation.intent.mutating,
            "destrutiva": foundation.intent.destructive,
            "efeitos_externos": foundation.intent.external_effects,
        },
        "qualidade_do_prompt": {
            "score": foundation.prompt_quality.score,
            "ambiguo": foundation.ambiguity.ambiguous,
            "confianca": analysis.confidence,
            "incerteza": analysis.uncertainty,
        },
        "raio_de_impacto": {
            "arquivos": len(radius.files),
            "modulos": len(radius.modules),
            "banco": len(radius.database),
            "usuarios": len(radius.users),
            "permissoes": len(radius.permissions),
            "ambientes": len(radius.environments),
            "integracoes_externas": len(radius.external_integrations),
            "fronteiras_de_seguranca": len(radius.security_boundaries),
            "magnitude": severity_label(radius.magnitude),
            "amplitude_de_fronteiras": metric.boundary_breadth if metric else None,
            "extensao_de_itens": metric.item_extent if metric else None,
        },
        "dimensoes_de_risco": [
            {
                "dimensao": dimension_label(item.dimension),
                "score": item.score,
                "severidade": severity_label(item.severity),
                "motivos": item.reason_codes,
            }
            for item in analysis.risk_dimensions
        ],
        "cenarios": [
            {
                "cenario": scenario_label(item.scenario),
                "modo": item.mode,
                "severidade": severity_label(item.severity),
                "gatilhos": item.trigger_codes,
                "efeito": item.expected_effect,
                "precondicoes": item.preconditions,
                "escopo_afetado": item.affected_scope,
                "contencao": item.containment,
                "rollback": rollback_label(item.rollback_requirement),
                "verificacao": item.verification,
                "risco_residual": severity_label(item.residual_risk),
                "confianca": item.confidence,
                "operacao_alvo_executada": item.target_operation_executed,
            }
            for item in analysis.simulations
        ],
        "evidencia_historica": {
            "fonte": analysis.historical_evidence.source,
            "status": analysis.historical_evidence.status,
            "amostra": analysis.historical_evidence.sample_size,
        },
        "achados": [
            {
                "titulo": item.title,
                "severidade": severity_label(item.severity),
                "motivo": item.reason_code,
            }
            for item in analysis.findings
        ],
        "recomendacoes": [
            {"acao": item.text, "base": item.basis} for item in result.recommendations
        ],
        "gate": {
            "interno": result.gate.value,
            "apresentado": gate_label(result.gate),
            "motivos": [
                {"codigo": code, "explicacao": reason_label(code)}
                for code in result.gate_reasons
            ],
        },
    }


def as_json(result: ConsoleAnalysis) -> str:
    return json.dumps(as_dict(result), ensure_ascii=False, indent=2, sort_keys=False)
