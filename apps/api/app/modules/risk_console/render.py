"""Renderizacao do resultado em texto, sem depender do framework de TUI.

Isto e uma funcao pura: analise entra, texto sai. Existe separada da tela por
dois motivos praticos.

Primeiro, teste. Verificar idioma, rotulo e presenca de secao num texto e
direto; verificar a mesma coisa numa captura de terminal e fragil e passa a
depender de largura de janela e de fonte.

Segundo, reuso. A CLI imprime o mesmo relatorio que a TUI mostra, entao um
usuario que le o resultado no console e outro que le no pipe veem exatamente
a mesma coisa — se fossem dois renderizadores, um dia divergiriam e ninguem
saberia qual estava certo.

Regra que atravessa o arquivo: so entra no texto o que existe na analise. Se
o motor nao trouxe evidencia historica, a secao nao aparece; ela nao e
preenchida com zeros para manter o layout bonito.
"""

from __future__ import annotations

from rich.markup import escape

from app.modules.risk_console.analysis import ConsoleAnalysis
from app.modules.risk_console.branding import (
    COLOR_ACCENT,
    COLOR_MUTED,
    PRODUCT_NAME,
    PRODUCT_SUBTITLE,
)
from app.modules.risk_console.domain import environment_label, executor_label, operation_label
from app.modules.risk_console.presentation import (
    ambiguity_label,
    dimension_label,
    gate_color,
    gate_label,
    percent,
    quality_label,
    reason_label,
    rollback_label,
    scenario_label,
    severity_color,
    severity_label,
)

LEADER_WIDTH = 26


def _row(label: str, value: str, color: str | None = None) -> str:
    """Linha com condutor pontilhado, como num laudo tecnico."""
    dots = "." * max(3, LEADER_WIDTH - len(label))
    painted = f"[{color}]{value}[/]" if color else value
    return f"  {escape(label)} {dots} {painted}"


def _title(text: str) -> str:
    return f"\n[bold {COLOR_ACCENT}]{escape(text)}[/]\n"


def _muted(text: str) -> str:
    return f"[{COLOR_MUTED}]{escape(text)}[/]"


def header() -> str:
    """Cabecalho do console — a identidade aprovada, num lugar so."""
    return (
        f"[bold {COLOR_ACCENT}]{escape(PRODUCT_NAME)}[/]\n"
        f"[{COLOR_MUTED}]{escape(PRODUCT_SUBTITLE)}[/]"
    )


def _executor_of(request) -> str:
    """`risk-console:claude-code` volta a ser 'Claude Code' na tela."""
    _, _, raw = request.agent_id.partition(":")
    return executor_label(raw or request.agent_id)


def render_intent(result: ConsoleAnalysis) -> str:
    intent = result.analysis.foundation.intent
    lines = [_title("INTENÇÃO")]
    lines.append(_row("Tipo de operação", operation_label(intent.operation)))
    if intent.inferred_operation != intent.operation:
        lines.append(_row("Operação inferida", operation_label(intent.inferred_operation)))
    lines.append(_row("Modificação", "SIM" if intent.mutating else "NÃO"))
    lines.append(_row("Destrutiva", "SIM" if intent.destructive else "NÃO"))
    lines.append(_row("Ambiente", environment_label(result.request.environment)))
    lines.append(_row("Executor", _executor_of(result.request)))
    return "\n".join(lines)


def render_quality(result: ConsoleAnalysis) -> str:
    analysis = result.analysis
    quality = analysis.foundation.prompt_quality
    lines = [_title("QUALIDADE DO PROMPT")]
    lines.append(_row("Qualidade", quality_label(quality.score)))
    lines.append(_row("Ambiguidade", ambiguity_label(analysis.foundation.ambiguity.ambiguous)))
    lines.append(_row("Confiança", percent(analysis.confidence)))
    lines.append(_row("Incerteza", percent(analysis.uncertainty)))
    return "\n".join(lines)


def render_blast_radius(result: ConsoleAnalysis) -> str:
    radius = result.analysis.blast_radius
    lines = [_title("RAIO DE IMPACTO")]
    lines.append(_row("Arquivos", str(len(radius.files))))
    lines.append(_row("Módulos", str(len(radius.modules))))
    lines.append(_row("Banco de dados", str(len(radius.database))))
    lines.append(_row("Usuários", str(len(radius.users))))
    lines.append(_row("Permissões", str(len(radius.permissions))))
    lines.append(_row("Ambientes", str(len(radius.environments))))
    lines.append(_row("Integrações externas", str(len(radius.external_integrations))))
    lines.append(_row("Fronteiras de segurança", str(len(radius.security_boundaries))))

    metric = radius.metric
    if metric is not None:
        lines.append(_row("Amplitude de fronteiras", str(metric.boundary_breadth)))
        lines.append(_row("Extensão de itens", str(metric.item_extent)))
    else:
        # Analise anterior ao Stage R3. Dizer isso e melhor que mostrar zero,
        # que seria indistinguivel de "nada foi atingido".
        lines.append(_row("Amplitude de fronteiras", "não medida"))
        lines.append(_row("Extensão de itens", "não medida"))

    lines.append(
        _row("Magnitude", severity_label(radius.magnitude), severity_color(radius.magnitude))
    )
    return "\n".join(lines)


def render_dimensions(result: ConsoleAnalysis) -> str:
    lines = [_title("DIMENSÕES DE RISCO")]
    for item in result.analysis.risk_dimensions:
        lines.append(
            _row(
                dimension_label(item.dimension),
                f"{severity_label(item.severity)}  ({item.score:.2f})",
                severity_color(item.severity),
            )
        )
    return "\n".join(lines)


def render_scenarios(result: ConsoleAnalysis) -> str:
    lines = [_title("SIMULAÇÃO DE CENÁRIOS")]
    lines.append(
        _muted("  Simulação analítica: nenhuma operação-alvo é executada.")
    )
    for item in result.analysis.simulations:
        color = severity_color(item.severity)
        lines.append("")
        lines.append(
            f"  [bold]{escape(scenario_label(item.scenario))}[/]"
            f"  [{color}]{escape(severity_label(item.severity))}[/]"
        )
        lines.append(f"    Efeito .............. {escape(item.expected_effect)}")
        if item.preconditions:
            lines.append(f"    Gatilho ............. {escape(', '.join(item.preconditions))}")
        if item.trigger_codes:
            lines.append(f"    Códigos ............. {escape(', '.join(item.trigger_codes))}")
        if item.affected_scope:
            lines.append(f"    Escopo afetado ...... {escape(', '.join(item.affected_scope))}")
        if item.containment:
            lines.append(f"    Contenção ........... {escape(item.containment)}")
        lines.append(
            f"    Rollback ............ {escape(rollback_label(item.rollback_requirement))}"
        )
        if item.verification:
            lines.append(f"    Verificação ......... {escape(', '.join(item.verification))}")
        lines.append(
            f"    Risco residual ...... {escape(severity_label(item.residual_risk))}"
        )
        lines.append(f"    Confiança ........... {percent(item.confidence)}")
    return "\n".join(lines)


def render_historical(result: ConsoleAnalysis) -> str:
    """Só aparece com dado real. Sem histórico, a seção não é desenhada."""
    evidence = result.analysis.historical_evidence
    if not evidence.sample_size and not evidence.items:
        return ""
    lines = [_title("EVIDÊNCIA HISTÓRICA")]
    lines.append(_row("Fonte", evidence.source))
    lines.append(_row("Situação", evidence.status))
    lines.append(_row("Amostra", str(evidence.sample_size)))
    for item in evidence.items:
        lines.append(
            _row(
                f"  {item.pattern_type.value}",
                f"confiança {percent(item.confidence)} · relevância {percent(item.relevance_score)}",
            )
        )
    return "\n".join(lines)


def render_findings(result: ConsoleAnalysis) -> str:
    lines = [_title("ACHADOS")]
    if not result.analysis.findings:
        lines.append(_muted("  Nenhum achado registrado."))
        return "\n".join(lines)
    for item in result.analysis.findings:
        color = severity_color(item.severity)
        lines.append(
            f"  [{color}]{escape(severity_label(item.severity))}[/]  "
            f"{escape(item.title)}  {_muted('(' + item.reason_code + ')')}"
        )
    return "\n".join(lines)


def render_recommendations(result: ConsoleAnalysis) -> str:
    lines = [_title("RECOMENDAÇÕES")]
    if not result.recommendations:
        lines.append(_muted("  Nenhuma recomendação adicional."))
        return "\n".join(lines)
    for item in result.recommendations:
        lines.append(f"  • {escape(item.text)}")
        lines.append(f"    {_muted('base: ' + item.basis)}")
    return "\n".join(lines)


def render_gate(result: ConsoleAnalysis) -> str:
    color = gate_color(result.gate)
    lines = [_title("GATE FINAL")]
    lines.append(f"  [bold {color}]{escape(gate_label(result.gate))}[/]")
    lines.append("")
    for code in result.gate_reasons:
        lines.append(f"  • {escape(reason_label(code))}  {_muted('[' + code + ']')}")
    if result.blocked:
        lines.append("")
        lines.append(
            f"  [bold {color}]EXECUÇÃO BLOQUEADA[/] "
            + _muted("— contrato e prompt aprovado indisponíveis neste estado.")
        )
    return "\n".join(lines)


def render_analysis(result: ConsoleAnalysis) -> str:
    """Relatório completo, na ordem em que se lê uma análise de risco."""
    blocks = [
        render_intent(result),
        render_quality(result),
        render_blast_radius(result),
        render_dimensions(result),
        render_scenarios(result),
        render_historical(result),
        render_findings(result),
        render_recommendations(result),
        render_gate(result),
    ]
    return "\n".join(block for block in blocks if block)
