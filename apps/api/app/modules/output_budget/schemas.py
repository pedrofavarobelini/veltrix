"""Tipos do orçamento de saída do provider (OUTPUT-BUDGET-CANCELLATION-01).

O orçamento é decidido exclusivamente pelo Veltrix. O consumidor não envia,
não sugere e não sobrescreve nenhum destes valores: `ChatRequest` continua sem
qualquer campo de tokens.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator


class BudgetSource(str, Enum):
    """Camada que efetivamente determinou o orçamento aplicado.

    Em empate, reporta-se a camada mais específica (task > modelo > global),
    porque é a que um operador ajustaria primeiro.
    """

    GLOBAL_CAP = "global_cap"
    MODEL_CAP = "model_cap"
    TASK_CAP = "task_cap"


class OutputBudget(BaseModel):
    """Resultado determinístico da composição dos tetos de saída."""

    model_config = ConfigDict(frozen=True)

    global_cap: int
    model_cap: int | None = None
    task_cap: int | None = None
    effective_budget: int
    budget_source: BudgetSource
    # True quando alguma camada declarada foi reduzida por outra mais estrita.
    budget_clamped: bool = False

    @model_validator(mode="after")
    def _check(self) -> OutputBudget:
        if self.global_cap <= 0:
            raise ValueError("global_cap deve ser inteiro positivo.")
        if self.model_cap is not None and self.model_cap <= 0:
            raise ValueError("model_cap deve ser inteiro positivo quando presente.")
        if self.task_cap is not None and self.task_cap <= 0:
            raise ValueError("task_cap deve ser inteiro positivo quando presente.")
        if self.effective_budget <= 0:
            raise ValueError("effective_budget deve ser inteiro positivo.")
        if self.effective_budget > self.global_cap:
            raise ValueError(
                "effective_budget nunca pode ultrapassar o teto global de segurança."
            )
        return self

    def as_audit_dict(self) -> dict[str, object]:
        """Projeção não sensível para auditoria e observabilidade."""
        return {
            "global_cap": self.global_cap,
            "model_cap": self.model_cap,
            "task_cap": self.task_cap,
            "effective_budget": self.effective_budget,
            "budget_source": self.budget_source.value,
            "budget_clamped": self.budget_clamped,
        }
