"""Renderizacao do resultado em texto, sem depender do framework de TUI.

Isto e uma funcao pura: analise entra, texto sai. Existe separada da tela por
dois motivos praticos.

Primeiro, teste. Verificar idioma, rotulo e presenca de secao num texto e
direto; verificar a mesma coisa numa captura de terminal e fragil e passa a
depender de largura de janela e de fonte.

Segundo, reuso. A CLI imprime o mesmo conteudo que a TUI mostra, so que em
sequencia; a TUI distribui os mesmos blocos em paineis. Se fossem dois
renderizadores, um dia divergiriam e ninguem saberia qual estava certo.

Regra que atravessa o arquivo: so entra no texto o que existe na analise. Se
o motor nao trouxe evidencia historica, a secao nao aparece; ela nao e
preenchida com zeros para manter o layout bonito.

Hierarquia de linguagem
-----------------------

O texto principal fala portugues. Codigo interno (`PROMPT_QUALITY_LOW`,
`FORBIDDEN_SCOPE`) e informacao de auditoria, nao de leitura: ele existe, mas
vive em `render_technical_details`. Quem precisa dele sabe procurar; quem esta
decidindo se executa um prompt precisa ler "Qualidade do prompt insuficiente".
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
    humanize_finding,
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


def _row(label: str, value: str, color: str | None = None, width: int = LEADER_WIDTH) -> str:
    """Linha com condutor pontilhado, como num laudo tecnico."""
    dots = "." * max(3, width - len(label))
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


# ---------------------------------------------------------------------------
# Paineis — blocos curtos, pensados para caber lado a lado
# ---------------------------------------------------------------------------


def render_summary_panel(result: ConsoleAnalysis) -> str:
    """As cinco perguntas de abertura: o que pretende, e o quao confiavel e.

    Intencao e qualidade juntas de proposito: "o que isto faz" e "o quanto o
    pedido esta bem escrito" sao lidas na mesma olhada, e separa-las obrigaria
    a percorrer duas regioes da tela para formar um juizo so.
    """
    analysis = result.analysis
    intent = analysis.foundation.intent
    quality = analysis.foundation.prompt_quality
    width = 22

    lines = [
        _row("Intenção", operation_label(intent.operation).upper(), COLOR_ACCENT, width),
    ]
    if intent.inferred_operation != intent.operation:
        lines.append(
            _row("Inferida do prompt", operation_label(intent.inferred_operation), None, width)
        )
    lines.append(
        _row(
            "Modifica",
            "SIM" if intent.mutating else "NÃO",
            severity_color(None) if not intent.mutating else None,
            width,
        )
    )
    if intent.destructive:
        lines.append(_row("Destrutiva", "SIM", severity_color(None), width))
    lines.append(_row("Ambiente", environment_label(result.request.environment), None, width))
    lines.append(_row("Executor", _executor_of(result.request), None, width))
    lines.append("")
    lines.append(_row("Qualidade do prompt", quality_label(quality.score), None, width))
    lines.append(
        _row(
            "Ambiguidade",
            ambiguity_label(analysis.foundation.ambiguity.ambiguous),
            None,
            width,
        )
    )
    lines.append(_row("Confiança", percent(analysis.confidence), None, width))
    lines.append(_row("Incerteza", percent(analysis.uncertainty), None, width))
    return "\n".join(lines)


def render_blast_panel(result: ConsoleAnalysis, columns: int = 2) -> str:
    """Alcance. Numeros crus, depois a metrica comparavel.

    Em duas colunas quando ha largura: sao doze linhas curtas, e empilha-las
    numa coluna so gastava vinte linhas de altura para mostrar dois digitos
    por linha, deixando dois tercos do painel em branco.
    """
    radius = result.analysis.blast_radius
    metric = radius.metric
    width = 26

    brutos = [
        ("Arquivos", str(len(radius.files)), None),
        ("Módulos", str(len(radius.modules)), None),
        ("Banco de dados", str(len(radius.database)), None),
        ("Usuários", str(len(radius.users)), None),
        ("Permissões", str(len(radius.permissions)), None),
        ("Ambientes", str(len(radius.environments)), None),
        ("Integrações externas", str(len(radius.external_integrations)), None),
        ("Fronteiras de segurança", str(len(radius.security_boundaries)), None),
    ]
    if metric is not None:
        derivados = [
            ("Amplitude de fronteiras", str(metric.boundary_breadth), None),
            ("Extensão de itens", str(metric.item_extent), None),
        ]
    else:
        # Analise anterior ao Stage R3. Dizer isso e melhor que mostrar zero,
        # que seria indistinguivel de "nada foi atingido".
        derivados = [
            ("Amplitude de fronteiras", "não medida", COLOR_MUTED),
            ("Extensão de itens", "não medida", COLOR_MUTED),
        ]
    derivados.append(
        ("Magnitude", severity_label(radius.magnitude), severity_color(radius.magnitude))
    )

    if columns < 2:
        linhas = [_row(*item, width) for item in brutos + [("", "", None)] + derivados]
        return "\n".join(line for line in linhas if line.strip())

    # Duas colunas: contagens a esquerda, metrica derivada a direita.
    esquerda = [_row(*item, width) for item in brutos]
    direita = [_row(*item, width) for item in derivados]
    altura = max(len(esquerda), len(direita))
    esquerda += [""] * (altura - len(esquerda))
    direita += [""] * (altura - len(direita))

    cell = 42
    linhas = []
    for a, b in zip(esquerda, direita):
        visivel = _visible_length(a)
        preenchimento = " " * max(1, cell - visivel)
        linhas.append(f"{a}{preenchimento}{b}" if b.strip() else a)
    return "\n".join(linhas)


def _visible_length(markup: str) -> int:
    """Comprimento sem as tags de cor, para alinhar colunas."""
    import re

    return len(re.sub(r"\[/?[^\]]*\]", "", markup))


def render_dimensions_band(result: ConsoleAnalysis, columns: int = 3) -> str:
    """Faixa compacta: nome em cima, severidade embaixo.

    A cor e REFORCO. O rotulo textual (BAIXO/MÉDIO/ALTO) vai junto sempre, de
    modo que a faixa continue legivel em terminal monocromatico ou para quem
    nao distingue as cores usadas.
    """
    items = result.analysis.risk_dimensions
    if not items:
        return _muted("  Nenhuma dimensão avaliada.")

    cell = 18
    lines: list[str] = []
    for start in range(0, len(items), columns):
        chunk = items[start : start + columns]
        nomes = "  ".join(
            f"[{COLOR_MUTED}]{escape(dimension_label(item.dimension)):<{cell}}[/]"
            for item in chunk
        )
        valores = "  ".join(
            f"[{severity_color(item.severity)}]{escape(severity_label(item.severity)):<{cell}}[/]"
            for item in chunk
        )
        lines.append("  " + nomes)
        lines.append("  " + valores)
        lines.append("")
    return "\n".join(lines).rstrip()



def render_context_panel(result: ConsoleAnalysis) -> str:
    """O contexto que a analise usou, com a ORIGEM de cada fato.

    Existe por causa de um problema real encontrado na homologacao: os campos
    avancados exibiam valores de demonstracao plausiveis, o formulario lia como
    preenchido, e a analise saiu com contexto que ninguem quis declarar.

    Os placeholders foram corrigidos. Este painel fecha a porta pelo outro
    lado: agora da para ver, antes de agir, exatamente o que foi declarado e o
    que nao foi.
    """
    from app.modules.risk_console.domain import (
        CONTEXT_FIELDS,
        PROVENANCE_LABELS,
        Provenance,
    )

    proveniencia = result.provenance or {}
    if not proveniencia:
        return _muted("  Origem do contexto não registrada nesta análise.")

    cores = {
        Provenance.DECLARED: COLOR_ACCENT,
        Provenance.INFERRED: None,
        Provenance.DEFAULTED: None,
        Provenance.UNKNOWN: COLOR_MUTED,
    }
    linhas = []
    for campo, rotulo in CONTEXT_FIELDS:
        origem = proveniencia.get(campo)
        if origem is None:
            continue
        linhas.append(
            _row(rotulo, PROVENANCE_LABELS[origem], cores[origem], 14)
        )
    declarados = sum(1 for o in proveniencia.values() if o is Provenance.DECLARED)
    linhas.append("")
    linhas.append(
        _muted(f"  {declarados} campo(s) declarado(s); o resto não entrou.")
    )
    return "\n".join(linhas)


def render_scenarios_summary(result: ConsoleAnalysis) -> str:
    """Cabecalho do painel de cenarios.

    A lista em si sao os proprios `Collapsible`, cujo titulo ja traz nome e
    severidade. Repetir a lista acima deles gastaria altura para dizer duas
    vezes a mesma coisa.
    """
    total = len(result.analysis.simulations)
    return _muted(f"  {total} cenário(s) — simulação analítica, nada é executado.")


def scenario_title(item, width: int = 26) -> str:
    """Titulo do cenario com condutor, no mesmo estilo do resto do laudo.

    Nome e severidade na mesma linha, alinhados — a severidade e o que se
    percorre com o olho, e ela precisa cair sempre na mesma coluna.
    """
    label = scenario_label(item.scenario)
    dots = "." * max(3, width - len(label))
    return f"{label} {dots} {severity_label(item.severity)}"


def render_scenario_detail(item) -> str:
    """Tudo o que o motor disse sobre UM cenario. Nada foi removido."""
    width = 18
    lines = [_row("Efeito", escape(item.expected_effect), None, width)]
    if item.preconditions:
        lines.append(_row("Gatilho", escape(", ".join(item.preconditions)), None, width))
    if item.affected_scope:
        lines.append(_row("Escopo afetado", escape(", ".join(item.affected_scope)), None, width))
    if item.containment:
        lines.append(_row("Contenção", escape(item.containment), None, width))
    lines.append(
        _row("Rollback", escape(rollback_label(item.rollback_requirement)), None, width)
    )
    if item.verification:
        lines.append(_row("Verificação", escape(", ".join(item.verification)), None, width))
    lines.append(
        _row(
            "Risco residual",
            severity_label(item.residual_risk),
            severity_color(item.residual_risk),
            width,
        )
    )
    lines.append(_row("Confiança", percent(item.confidence), None, width))
    return "\n".join(lines)


def render_historical_panel(result: ConsoleAnalysis) -> str:
    """Só mostra o que existe. Sem histórico, diz que não há — e não zera."""
    evidence = result.analysis.historical_evidence
    if not evidence.sample_size and not evidence.items:
        return _muted("  Sem histórico comparável para este projeto.")

    width = 20
    lines = [
        _row("Amostra", str(evidence.sample_size), None, width),
        _row("Situação", evidence.status, None, width),
    ]
    if evidence.items:
        lines.append("")
        for item in evidence.items[:6]:
            lines.append(
                f"  {escape(item.pattern_type.value)} "
                f"{_muted('confiança ' + percent(item.confidence))}"
            )
    return "\n".join(lines)


def render_findings_panel(result: ConsoleAnalysis) -> str:
    """O que está errado ou perigoso, em português. Códigos ficam de fora."""
    findings = result.analysis.findings
    if not findings:
        return _muted("  Nenhum achado registrado.")
    lines = []
    for item in findings:
        color = severity_color(item.severity)
        lines.append(
            f"  [{color}]{escape(severity_label(item.severity))}[/]  "
            f"{escape(humanize_finding(item.title))}"
        )
    return "\n".join(lines)


def render_recommendations_panel(result: ConsoleAnalysis) -> str:
    """O que fazer a respeito. Separado dos achados de propósito."""
    if not result.recommendations:
        return _muted("  Nenhuma recomendação adicional.")
    return "\n".join(f"  • {escape(item.text)}" for item in result.recommendations)


def render_gate_banner(result: ConsoleAnalysis) -> str:
    """O veredito, com o motivo principal logo abaixo.

    Uma linha grande e um motivo. O resto dos motivos fica nos detalhes: quem
    esta decidindo precisa da resposta, nao da lista inteira.
    """
    color = gate_color(result.gate)
    label = gate_label(result.gate)
    lines = [f"[bold {color}]{escape(label)}[/]"]
    if result.gate_reasons:
        lines.append(_muted(reason_label(result.gate_reasons[0])))
    if result.blocked:
        lines.append(
            f"[bold {color}]EXECUÇÃO BLOQUEADA[/] "
            + _muted("— contrato e prompt aprovado indisponíveis.")
        )
    return "\n".join(lines)


def render_technical_details(result: ConsoleAnalysis) -> str:
    """Auditoria: códigos, políticas, identificadores e scores.

    Existe para que nada seja escondido — e fica recolhido para que nada disso
    dispute atenção com a decisão.
    """
    analysis = result.analysis
    width = 26
    lines = [
        _row("Gate (interno)", result.gate.value, None, width),
        _row("Motivos do gate", ", ".join(result.gate_reasons) or "—", None, width),
        _row("Análise", analysis.analysis_id, None, width),
        _row("Requisição", analysis.request_id, None, width),
        _row("Projeto", analysis.project_id, None, width),
        _row("Política de risco", analysis.policy_version, None, width),
        _row("Política da fundação", analysis.foundation.policy_version, None, width),
        _row("Operação-alvo executada", str(analysis.target_operation_executed), None, width),
        _row("Provider chamado", str(analysis.provider_called), None, width),
    ]
    metric = analysis.blast_radius.metric
    if metric is not None:
        lines.append(_row("Métrica de alcance", metric.metric_version, None, width))
        lines.append(
            _row("Contagem por fronteira", str(metric.boundary_counts), None, width)
        )

    lines.append(_title("Dimensões (score)"))
    for item in analysis.risk_dimensions:
        lines.append(
            _row(
                dimension_label(item.dimension),
                f"{item.score:.2f}  {', '.join(item.reason_codes) or '—'}",
                None,
                width,
            )
        )

    if analysis.findings:
        lines.append(_title("Achados (reason codes)"))
        for item in analysis.findings:
            lines.append(_row(item.reason_code, item.title, None, width))

    if analysis.deterministic_rules:
        lines.append(_title("Regras determinísticas"))
        for item in analysis.deterministic_rules:
            lines.append(
                _row(item.rule_id, f"{item.reason_code} · {item.severity.value}", None, width)
            )

    if result.recommendations:
        lines.append(_title("Base das recomendações"))
        for item in result.recommendations:
            lines.append(f"  {_muted(item.basis)}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Relatorio linear — usado pela CLI e pelo arquivo exportado em texto
# ---------------------------------------------------------------------------


def render_intent(result: ConsoleAnalysis) -> str:
    return _title("INTENÇÃO") + render_summary_panel(result)


def render_quality(result: ConsoleAnalysis) -> str:
    analysis = result.analysis
    quality = analysis.foundation.prompt_quality
    return "\n".join(
        [
            _title("QUALIDADE DO PROMPT"),
            _row("Qualidade", quality_label(quality.score)),
            _row("Ambiguidade", ambiguity_label(analysis.foundation.ambiguity.ambiguous)),
            _row("Confiança", percent(analysis.confidence)),
            _row("Incerteza", percent(analysis.uncertainty)),
        ]
    )


def render_blast_radius(result: ConsoleAnalysis) -> str:
    return _title("RAIO DE IMPACTO") + render_blast_panel(result)


def render_dimensions(result: ConsoleAnalysis) -> str:
    lines = [_title("DIMENSÕES DE RISCO")]
    for item in result.analysis.risk_dimensions:
        lines.append(
            _row(
                dimension_label(item.dimension),
                severity_label(item.severity),
                severity_color(item.severity),
            )
        )
    return "\n".join(lines)


def render_scenarios(result: ConsoleAnalysis) -> str:
    lines = [_title("SIMULAÇÃO DE CENÁRIOS")]
    for item in result.analysis.simulations:
        lines.append("")
        lines.append(
            f"  [bold]{escape(scenario_label(item.scenario))}[/]  "
            f"[{severity_color(item.severity)}]{escape(severity_label(item.severity))}[/]"
        )
        lines.append(render_scenario_detail(item))
    return "\n".join(lines)


def render_historical(result: ConsoleAnalysis) -> str:
    evidence = result.analysis.historical_evidence
    if not evidence.sample_size and not evidence.items:
        return ""
    return _title("EVIDÊNCIA HISTÓRICA") + render_historical_panel(result)


def render_findings(result: ConsoleAnalysis) -> str:
    return _title("ACHADOS") + render_findings_panel(result)


def render_recommendations(result: ConsoleAnalysis) -> str:
    return _title("RECOMENDAÇÕES") + render_recommendations_panel(result)


def render_gate(result: ConsoleAnalysis) -> str:
    color = gate_color(result.gate)
    lines = [_title("GATE FINAL"), f"  [bold {color}]{escape(gate_label(result.gate))}[/]", ""]
    for code in result.gate_reasons:
        lines.append(f"  • {escape(reason_label(code))}")
    if result.blocked:
        lines.append("")
        lines.append(
            f"  [bold {color}]EXECUÇÃO BLOQUEADA[/] "
            + _muted("— contrato e prompt aprovado indisponíveis neste estado.")
        )
    return "\n".join(lines)


def render_analysis(result: ConsoleAnalysis) -> str:
    """Relatório completo, na ordem em que se lê uma análise de risco.

    O gate vem CEDO — logo depois do resumo — porque é a resposta que se
    procura. Os detalhes que a sustentam vêm em seguida, e os códigos internos
    ficam por último, onde servem de auditoria e não de leitura.
    """
    blocks = [
        render_intent(result),
        render_blast_radius(result),
        render_dimensions(result),
        render_gate(result),
        render_quality(result),
        render_scenarios(result),
        render_historical(result),
        render_findings(result),
        render_recommendations(result),
        _title("DETALHES TÉCNICOS") + render_technical_details(result),
    ]
    return "\n".join(block for block in blocks if block)
