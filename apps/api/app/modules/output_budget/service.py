"""Resolução determinística do orçamento de saída (OUTPUT-BUDGET-CANCELLATION-01).

Antes desta frente o adapter Gemini chamava `generate_content` sem nenhuma
configuração de geração: o limite de saída ficava inteiramente sob o default do
modelo, fora do controle do PedroCore. Este módulo passa a decidir o teto:

    effective_output_budget = min(global_cap, model_cap, task_cap)

Propriedades garantidas:

  - o consumidor NUNCA participa: `ChatRequest` não tem campo de tokens e nada
    aqui lê payload, metadata, context ou variável enviada pelo FinGuard;
  - a função de resolução é pura: mesmas entradas, mesmo resultado;
  - valores inválidos (não inteiros, zero, negativos, booleanos) são
    descartados em vez de propagados;
  - task não catalogada recebe o teto conservador, nunca o teto global.

Justificativa dos valores adotados
----------------------------------

Os tetos abaixo são decisão de engenharia derivada do `response_style` de cada
task no `task_router`, não de medição de tokens: até esta frente o
`usage_metadata` era descartado e o repositório nunca teve contagem real de
tokens. São deliberadamente generosos para não truncar resposta legítima, e
finitos para que nenhuma geração fique sem teto.

  - `_ASSISTANT_CAP` (4096) — tasks conversacionais e financeiras
    (`assistant_chat`, `ecosystem_assistant`, `finance_advice`,
    `technical_explanation`, `code_help`). São as respostas mais longas e mais
    livres do sistema; os cenários homologados do FinGuard (Dívidas,
    Economizar, Crescer) e o pendente (Organizar) vivem aqui. 4096 tokens
    comportam um plano financeiro completo com folga de várias vezes o tamanho
    observado nas respostas homologadas.
  - `_STRUCTURED_CAP` (3072) — tasks de QA, relatório, exploração e
    planejamento. A resposta é enumerativa e naturalmente limitada pelo
    esqueleto estruturado.
  - `_CONSERVATIVE_CAP` (2048) — task desconhecida ou não catalogada. Sem
    caracterização, o sistema assume o menor teto.
  - `GLOBAL_OUTPUT_SAFETY_CAP` (8192) — teto absoluto. Nenhuma composição de
    catálogo ou política pode ultrapassá-lo.

Estes números podem precisar de ajuste depois de uma sonda real autorizada que
meça `usage_metadata` em produção. Nada nesta frente mediu tokens reais.
"""

from __future__ import annotations

from app.modules.output_budget.schemas import BudgetSource, OutputBudget

# Teto absoluto de segurança. Nenhum orçamento efetivo o ultrapassa.
GLOBAL_OUTPUT_SAFETY_CAP = 8192

# Faixas por natureza de resposta (ver justificativa no docstring do módulo).
_ASSISTANT_CAP = 4096
_STRUCTURED_CAP = 3072
_CONSERVATIVE_CAP = 2048

# Teto aplicado a qualquer task fora do catálogo abaixo.
DEFAULT_TASK_OUTPUT_CAP = _CONSERVATIVE_CAP

# Derivação do timeout de transporte a partir do orçamento temporal da
# orquestração. A regra vive num único lugar e garante, para QUALQUER valor
# aceito por `_provider_timeout_seconds` (clamp [0.05 s, 120 s]), que o
# transporte expira ANTES da espera externa — deixando folga determinística
# para propagar a exceção, fechar o cliente, auditar e aplicar o fallback.
TRANSPORT_TIMEOUT_SAFETY_MARGIN_SECONDS = 2.0
TRANSPORT_TIMEOUT_MAX_RATIO = 0.9
MIN_TRANSPORT_TIMEOUT_SECONDS = 1.0

# Política interna por task. Espelha os `task_type` do task_router; uma task
# ausente aqui não é erro — recebe DEFAULT_TASK_OUTPUT_CAP.
_TASK_OUTPUT_CAPS: dict[str, int] = {
    # Conversacional / assistente / financeiro.
    "assistant_chat": _ASSISTANT_CAP,
    "ecosystem_assistant": _ASSISTANT_CAP,
    "finance_advice": _ASSISTANT_CAP,
    "technical_explanation": _ASSISTANT_CAP,
    "code_help": _ASSISTANT_CAP,
    "general_chat": _STRUCTURED_CAP,
    "local_model_chat": _STRUCTURED_CAP,
    # Estruturado: QA, relatório, exploração, planejamento.
    "qa_report_analysis": _STRUCTURED_CAP,
    "qa_failure_diagnosis": _STRUCTURED_CAP,
    "release_gate_review": _STRUCTURED_CAP,
    "artifact_summary": _STRUCTURED_CAP,
    "exploratory_test_plan": _STRUCTURED_CAP,
    "manual_exploration_report": _STRUCTURED_CAP,
    "assisted_exploration_review": _STRUCTURED_CAP,
    "report_ingestion": _STRUCTURED_CAP,
    "project_memory_summary": _STRUCTURED_CAP,
    "model_foundation_review": _STRUCTURED_CAP,
    "intelligence_planning": _STRUCTURED_CAP,
    "project_status": _STRUCTURED_CAP,
    "report_memory_query": _STRUCTURED_CAP,
    "evaluation_run": _STRUCTURED_CAP,
    # Task desconhecida normalizada pelo task_router.
    "unknown": _CONSERVATIVE_CAP,
}


def _valid_cap(value: object) -> int | None:
    """Aceita somente inteiro estritamente positivo.

    `bool` é subclasse de `int` em Python e nunca é um teto legítimo, por isso
    é rejeitado explicitamente.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value > 0 else None


class OutputBudgetService:
    """Política pura de orçamento de saída. Não conhece payload nem caller."""

    def global_cap(self) -> int:
        return GLOBAL_OUTPUT_SAFETY_CAP

    def task_cap(self, task_type: str | None) -> int:
        normalized = (task_type or "").strip().lower()
        return _TASK_OUTPUT_CAPS.get(normalized, DEFAULT_TASK_OUTPUT_CAP)

    @staticmethod
    def transport_timeout_ms(orchestration_timeout_seconds: float) -> int:
        """Deriva o timeout do transporte em MILISSEGUNDOS.

        `PEDROCORE_PROVIDER_TIMEOUT_SECONDS` está em segundos e
        `HttpOptions.timeout` em milissegundos: a conversão acontece uma única
        vez, aqui. O resultado é sempre estritamente menor que a espera da
        orquestração, inclusive nos extremos do clamp.
        """
        with_margin = max(
            orchestration_timeout_seconds - TRANSPORT_TIMEOUT_SAFETY_MARGIN_SECONDS,
            MIN_TRANSPORT_TIMEOUT_SECONDS,
        )
        seconds = min(
            with_margin,
            orchestration_timeout_seconds * TRANSPORT_TIMEOUT_MAX_RATIO,
        )
        return max(1, int(seconds * 1_000))

    def resolve(
        self,
        *,
        task_type: str | None,
        model_cap: object = None,
    ) -> OutputBudget:
        """Compõe o orçamento efetivo pelo menor teto declarado e válido."""
        global_cap = self.global_cap()
        task_cap = self.task_cap(task_type)
        valid_model_cap = _valid_cap(model_cap)

        candidates: list[tuple[BudgetSource, int]] = [
            (BudgetSource.GLOBAL_CAP, global_cap),
            (BudgetSource.TASK_CAP, task_cap),
        ]
        if valid_model_cap is not None:
            candidates.append((BudgetSource.MODEL_CAP, valid_model_cap))

        effective = min(value for _, value in candidates)

        # Empate resolve para a camada mais específica: task > modelo > global.
        precedence = {
            BudgetSource.TASK_CAP: 0,
            BudgetSource.MODEL_CAP: 1,
            BudgetSource.GLOBAL_CAP: 2,
        }
        source = min(
            (item for item in candidates if item[1] == effective),
            key=lambda item: precedence[item[0]],
        )[0]

        clamped = any(value > effective for _, value in candidates)

        return OutputBudget(
            global_cap=global_cap,
            model_cap=valid_model_cap,
            task_cap=task_cap,
            effective_budget=effective,
            budget_source=source,
            budget_clamped=clamped,
        )


output_budget_service = OutputBudgetService()
