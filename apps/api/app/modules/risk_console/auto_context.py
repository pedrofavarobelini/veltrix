"""Ponte entre o Auto Context e o formulario do console.

Responsabilidades, e so estas:

1. montar a proposta a partir do que o formulario ja tem;
2. aplicar a proposta CONFIRMADA sobre a entrada, sem sobrescrever declaracao;
3. renderizar a tela de revisao.

O que ela nao faz: decidir. A proposta vira `ConsoleRequestInput`, o motor
analisa, e o gate continua sendo do Risk Engine.
"""

from __future__ import annotations

from rich.markup import escape

from app.modules.risk_console.branding import COLOR_ACCENT, COLOR_MUTED, COLOR_WARN
from app.modules.risk_console.domain import ConsoleRequestInput
from app.modules.risk_engine.schemas import OperationKind
from app.modules.risk_intake.builder import auto_context_builder
from app.modules.risk_intake.schemas import (
    ContextOrigin,
    ContextProposal,
    EffectivePermission,
)

REVIEW_NOTICE = (
    "O Veltrix identificou automaticamente operação, escopo, permissões e "
    "restrições a partir do prompt e do contexto do projeto. Revise "
    "principalmente os itens inferidos antes de continuar. A confirmação "
    "autoriza somente a análise de risco; nenhuma operação será executada."
)


def propose(entry: ConsoleRequestInput) -> ContextProposal:
    """Proposta para a entrada atual do formulario.

    O que o humano ja declarou entra como `declared` e tem precedencia: o
    builder propoe onde falta, e nunca por cima.
    """
    declarado: dict[str, tuple[str, ...]] = {}
    for nome, valores in (
        ("targets", entry.targets),
        ("allowed_scope", entry.allowed_scope),
        ("forbidden_scope", entry.forbidden_scope),
        ("required_tests", entry.required_tests),
        ("requested_permissions", entry.permissions),
    ):
        if valores:
            declarado[nome] = tuple(valores)
    if entry.database:
        declarado["database"] = (entry.database,)
    if entry.operation is not None:
        declarado["operation"] = (entry.operation.value,)

    from app.modules.risk_console.domain import environment_value, executor_value

    return auto_context_builder.build(
        prompt=entry.prompt,
        project_id=entry.project_id,
        environment=environment_value(entry.environment_label),
        executor=executor_value(entry.executor_label),
        declared=declarado,
    )


def apply(entry: ConsoleRequestInput, proposal: ContextProposal) -> ConsoleRequestInput:
    """Aplica a proposta CONFIRMADA sobre a entrada.

    Campo declarado pelo humano nunca e sobrescrito — o builder ja o devolveu
    como DECLARED, e aqui ele so e reescrito por ele mesmo.

    `effective_permissions` e o que vira permissao da requisicao, e nao
    `requested_permissions`: pedir nao e receber, e submeter o pedido como se
    fosse concessao apagaria a interseccao inteira.
    """
    import dataclasses

    atualizacao: dict = {}
    # A origem de cada campo resolvido viaja junto. Sem isto, o painel de
    # contexto so via "tem valor" e concluia "foi declarado" — e confirmar uma
    # inferencia passava a parecer que o humano a tinha digitado.
    origens: dict[str, str] = {}
    confirmados: set[str] = set()

    def _registrar(campo: str, nome_proposta: str) -> None:
        proposto = proposal.field(nome_proposta)
        if proposto is None:
            return
        origens[campo] = proposto.origin.value
        confirmados.add(campo)

    operacao = proposal.field("operation")
    if operacao and operacao.values and entry.operation is None:
        atualizacao["operation"] = OperationKind(operacao.values[0])
        _registrar("operation", "operation")

    alvos = proposal.field("targets")
    if alvos and alvos.values and not entry.targets:
        atualizacao["targets"] = list(alvos.values)
        _registrar("targets", "targets")

    escopo = proposal.field("allowed_scope")
    if escopo and escopo.values and not entry.allowed_scope:
        atualizacao["allowed_scope"] = list(escopo.values)
        _registrar("allowed_scope", "allowed_scope")

    proibido = proposal.field("forbidden_scope")
    if proibido and proibido.values:
        atualizacao["forbidden_scope"] = list(
            dict.fromkeys([*entry.forbidden_scope, *proibido.values])
        )
        if not entry.forbidden_scope:
            _registrar("forbidden_scope", "forbidden_scope")

    testes = proposal.field("required_tests")
    if testes and testes.values and not entry.required_tests:
        atualizacao["required_tests"] = list(testes.values)
        _registrar("required_tests", "required_tests")

    if not entry.permissions:
        # So o que a interseccao concedeu. Uma capacidade pedida e negada NAO
        # entra: ela e conflito, e conflito e para o gate ver.
        concedidas = [
            item.capability.value
            for item in proposal.permissions
            if item.effective is EffectivePermission.GRANTED
        ]
        # `prefixo:alvo`, e nao `prefixo:capacidade`. O motor casa pelo
        # prefixo, mas a permissao tambem e LIDA por humano — e "write:write"
        # nao diz onde a escrita foi permitida.
        alvos = list(atualizacao.get("targets") or entry.targets)
        if alvos and concedidas:
            atualizacao["permissions"] = sorted(
                {f"{_permission_prefix(item)}:{alvos[0]}" for item in concedidas}
            )
            # Permissao efetiva e decisao de POLITICA, e nao declaracao do
            # humano nem inferencia do texto.
            origens["permissions"] = "POLICY_DERIVED"
            confirmados.add("permissions")
        # Sem alvo identificado, NENHUMA permissao e proposta. Inventar um
        # escopo amplo — `write:projeto` — para um pedido como "corrija tudo"
        # seria fabricar autorizacao ampla a partir de ambiguidade. Sem
        # permissao, o motor bloqueia, e a ambiguidade aparece em vez de sumir.

    banco = proposal.field("database")
    if banco and banco.values and not entry.database:
        atualizacao["database"] = banco.values[0]
        _registrar("database", "database")

    if not atualizacao:
        return entry
    atualizacao["resolved_origins"] = {**entry.resolved_origins, **origens}
    atualizacao["confirmed_fields"] = frozenset(entry.confirmed_fields | confirmados)
    return dataclasses.replace(entry, **atualizacao)


def _permission_prefix(capability: str) -> str:
    """Traduz capacidade tecnica para o prefixo que o motor V1 espera.

    O motor casa `write:`, `read:`, `execute:`, `migrate:`. A traducao vive
    aqui, na fronteira, e nao no motor — que nao precisa conhecer o
    vocabulario tecnico do intake.
    """
    if capability.startswith("filesystem.read"):
        return "read"
    if capability.startswith("filesystem.write"):
        return "write"
    if capability.startswith("database.migration"):
        return "migrate"
    if capability.startswith("database"):
        return "migrate"
    if capability.startswith("deployment"):
        return "deploy"
    return "execute"


def render_review(proposal: ContextProposal) -> str:
    """A tela de revisao. Compacta: resumo, conflito e contagem."""
    linhas = [f"[{COLOR_MUTED}]{escape(REVIEW_NOTICE)}[/]", ""]

    grupos = (
        ("DECLARADO", ContextOrigin.DECLARED, COLOR_ACCENT),
        ("INFERIDO", ContextOrigin.INFERRED, None),
        ("POLICY", ContextOrigin.POLICY_DERIVED, None),
        ("DESCONHECIDO", ContextOrigin.UNKNOWN, COLOR_MUTED),
    )
    for titulo, origem, cor in grupos:
        itens = [item for item in proposal.fields if item.origin is origem]
        if not itens:
            continue
        pintado = f"[{cor}]{titulo}[/]" if cor else f"[bold]{titulo}[/]"
        linhas.append(f"  {pintado}")
        for item in itens:
            valores = ", ".join(item.values) if item.values else "—"
            marca = " ⚠" if item.confirmation_required else ""
            linhas.append(
                f"    {escape(item.label)}: {escape(valores)}"
                f" [{COLOR_MUTED}]({item.confidence.value.lower()}){marca}[/]"
            )
        linhas.append("")

    conflitos = proposal.conflicts
    if conflitos:
        # Conflito e a informacao mais importante da proposta: e onde o pedido
        # e a realidade discordam. Nunca fica escondido atras de "detalhes".
        linhas.append(f"  [{COLOR_WARN}]CONFLITO[/]")
        for item in conflitos:
            linhas.append(
                f"    {escape(item.capability.value)}: {escape(item.explanation)}"
            )
        linhas.append("")

    linhas.append(
        f"  [{COLOR_MUTED}]{proposal.declared_count} declarado(s) · "
        f"{proposal.inferred_count} inferido(s) · "
        f"{proposal.policy_count} política(s) · "
        f"{proposal.review_count} requer(em) revisão[/]"
    )
    return "\n".join(linhas)
