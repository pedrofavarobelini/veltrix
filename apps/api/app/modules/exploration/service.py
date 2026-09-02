import re

from app.modules.contracts import codes
from app.modules.exploration.schemas import ExplorationPlan

# Agente exploratório assistido (Bloco 11): gera plano/checklist manual de
# forma local e determinística. Nunca executa ações, nunca abre navegador,
# nunca roda Playwright, nunca chama provider real, nunca acessa FinGuard real.

EXPLORATION_TASK_TYPES = {
    "exploratory_test_plan",
    "manual_exploration_report",
    "assisted_exploration_review",
}

ASSISTED_ONLY_WARNING = (
    "Exploração em modo assistido: o Veltrix apenas sugere passos manuais; "
    "nenhuma ação é executada automaticamente."
)

HUMAN_CONFIRMATION_WARNING = (
    "Confirmação humana obrigatória: o resultado da exploração deve ser "
    "validado por uma pessoa antes de qualquer decisão."
)

CANNOT_EXECUTE_WARNING = (
    "O agente exploratório não executa comandos, não abre navegador e não "
    "interage com sistemas reais."
)

ACTION_BLOCKED_WARNING = (
    "Ação potencialmente destrutiva ou automática solicitada foi bloqueada; "
    "somente passos manuais são sugeridos."
)

BLOCKED_ACTIONS = [
    "Abrir navegador automaticamente.",
    "Clicar, digitar ou navegar em sistema real.",
    "Executar Playwright ou automação de UI.",
    "Executar comandos de terminal.",
    "Criar, alterar ou deletar dados reais.",
    "Chamar provider real de IA.",
    "Acessar o repositório ou ambiente real do FinGuard.",
    "Aprovar release automaticamente com base neste plano.",
]

_DESTRUCTIVE_PATTERN = re.compile(
    r"\b(delete|drop|truncate|apagar|resetar|excluir|deletar|"
    r"executar comando|rodar comando|execute|rode o comando)\b",
    re.IGNORECASE,
)

_RISK_KEYWORDS = {
    "login": "Autenticação/login",
    "auth": "Autenticação/login",
    "senha": "Autenticação/credenciais",
    "pagamento": "Fluxo financeiro/pagamentos",
    "payment": "Fluxo financeiro/pagamentos",
    "transaç": "Fluxo financeiro/transações",
    "banco": "Banco de dados",
    "database": "Banco de dados",
    "migration": "Migrations/estrutura de dados",
    "produção": "Ambiente de produção",
    "production": "Ambiente de produção",
    "dashboard": "Dashboard/visualização",
    "relatório": "Relatórios",
}


def _extract_routes(payload_context: dict | None, payload_metadata: dict | None) -> list[str]:
    for source in (payload_context, payload_metadata):
        if not source:
            continue
        for key in ("routes", "screens", "telas", "rotas"):
            value = source.get(key)
            if isinstance(value, list):
                return [str(item) for item in value if str(item).strip()]
    return []


class ExplorationService:
    def build(
        self,
        task_type: str,
        message: str,
        payload_context: dict | None = None,
        payload_metadata: dict | None = None,
    ) -> ExplorationPlan | None:
        if task_type not in EXPLORATION_TASK_TYPES:
            return None

        routes = _extract_routes(payload_context, payload_metadata)
        text_for_risk = " ".join(
            [message or ""] + routes
        ).lower()

        risk_areas = sorted({
            label
            for keyword, label in _RISK_KEYWORDS.items()
            if keyword in text_for_risk
        })
        if not risk_areas:
            risk_areas = ["Fluxos críticos indicados pelo usuário (a confirmar)."]

        manual_steps: list[str] = []
        for route in routes:
            manual_steps.append(
                f"Abrir manualmente '{route}', verificar carregamento, estados de "
                "erro e comportamento esperado; registrar evidência textual."
            )
        if not manual_steps:
            manual_steps.append(
                "Listar manualmente as telas/rotas do fluxo alvo e percorrê-las uma a uma."
            )
        manual_steps.extend(
            [
                "Testar entradas inválidas e limites em formulários do fluxo.",
                "Verificar mensagens de erro e estados vazios.",
                "Registrar cada resultado como artefato textual (relatório/log) para análise QA local.",
            ]
        )

        exploration_plan = [
            f"Objetivo: {message.strip() or 'Exploração manual do fluxo alvo.'}",
            "Escopo: somente exploração manual assistida; nenhuma ação automática.",
            f"Rotas/telas mapeadas: {len(routes)} fornecida(s) pelo usuário.",
            "Critério de saída: evidências textuais coletadas e revisadas por humano.",
        ]

        required_evidence = [
            "Relatório textual da exploração (passos executados e resultados).",
            "Logs ou saídas de teste relevantes em formato texto.",
            "Screenshots apenas como apoio — exigem revisão humana (QA visual real não habilitado).",
        ]

        human_confirmations = [
            "Confirmar que a exploração foi executada por uma pessoa.",
            "Confirmar que nenhum dado real foi alterado durante a exploração.",
            "Confirmar a conclusão (aprovado/reprovado) com base nas evidências.",
        ]

        warnings = [
            ASSISTED_ONLY_WARNING,
            HUMAN_CONFIRMATION_WARNING,
            CANNOT_EXECUTE_WARNING,
        ]
        warning_codes = [
            codes.EXPLORATION_ASSISTED_ONLY,
            codes.HUMAN_CONFIRMATION_REQUIRED,
            codes.EXPLORATION_CANNOT_EXECUTE_COMMANDS,
        ]

        if _DESTRUCTIVE_PATTERN.search(message or ""):
            warnings.append(ACTION_BLOCKED_WARNING)
            warning_codes.append(codes.EXPLORATION_ACTION_BLOCKED)

        return ExplorationPlan(
            task_type=task_type,
            objective=(message or "").strip(),
            exploration_plan=exploration_plan,
            manual_steps=manual_steps,
            risk_areas=risk_areas,
            required_evidence=required_evidence,
            human_confirmations=human_confirmations,
            blocked_actions=list(BLOCKED_ACTIONS),
            can_execute_actions=False,
            can_advance=False,
            requires_human_review=True,
            warnings=warnings,
            warning_codes=warning_codes,
        )


exploration_service = ExplorationService()
