"""Política de orçamento de saída (OUTPUT-BUDGET-CANCELLATION-01).

Cobre a resolução pura do orçamento, a derivação do timeout de transporte e a
invariante de que o consumidor nunca participa dessas decisões.
"""

from __future__ import annotations

import pytest

from app.modules.chat.schemas import ChatRequest
from app.modules.output_budget.schemas import BudgetSource, OutputBudget
from app.modules.output_budget.service import (
    DEFAULT_TASK_OUTPUT_CAP,
    GLOBAL_OUTPUT_SAFETY_CAP,
    MIN_TRANSPORT_TIMEOUT_SECONDS,
    TRANSPORT_TIMEOUT_MAX_RATIO,
    output_budget_service,
)
from app.modules.provider_catalog.service import provider_catalog_service


# ---------------------------------------------------------------- composição


def test_global_safety_cap_is_the_absolute_ceiling():
    budget = output_budget_service.resolve(task_type="assistant_chat", model_cap=999_999)

    assert budget.effective_budget <= GLOBAL_OUTPUT_SAFETY_CAP
    assert budget.global_cap == GLOBAL_OUTPUT_SAFETY_CAP


def test_model_cap_wins_when_it_is_the_strictest_layer():
    budget = output_budget_service.resolve(task_type="assistant_chat", model_cap=512)

    assert budget.effective_budget == 512
    assert budget.budget_source is BudgetSource.MODEL_CAP
    assert budget.budget_clamped is True


def test_task_cap_wins_when_it_is_the_strictest_layer():
    budget = output_budget_service.resolve(task_type="assistant_chat", model_cap=8192)

    assert budget.effective_budget == output_budget_service.task_cap("assistant_chat")
    assert budget.budget_source is BudgetSource.TASK_CAP
    assert budget.budget_clamped is True


def test_effective_budget_is_the_minimum_of_all_declared_caps():
    budget = output_budget_service.resolve(task_type="qa_report_analysis", model_cap=700)

    assert budget.effective_budget == min(
        budget.global_cap, budget.model_cap, budget.task_cap
    )


def test_unknown_task_falls_back_to_the_conservative_cap():
    budget = output_budget_service.resolve(
        task_type="task_que_nao_existe", model_cap=8192
    )

    assert budget.task_cap == DEFAULT_TASK_OUTPUT_CAP
    assert budget.effective_budget == DEFAULT_TASK_OUTPUT_CAP
    assert DEFAULT_TASK_OUTPUT_CAP < GLOBAL_OUTPUT_SAFETY_CAP


def test_model_without_declared_cap_still_gets_global_and_task_limits():
    budget = output_budget_service.resolve(task_type="assistant_chat", model_cap=None)

    assert budget.model_cap is None
    assert budget.effective_budget == output_budget_service.task_cap("assistant_chat")
    assert budget.budget_source is BudgetSource.TASK_CAP


@pytest.mark.parametrize("invalid", [0, -1, -8192, "4096", 4096.0, None, True, False])
def test_invalid_model_cap_is_discarded_instead_of_propagated(invalid):
    budget = output_budget_service.resolve(task_type="assistant_chat", model_cap=invalid)

    assert budget.model_cap is None
    assert budget.effective_budget > 0


def test_budget_is_never_clamped_flag_when_all_layers_agree():
    cap = output_budget_service.task_cap("assistant_chat")
    budget = OutputBudget(
        global_cap=cap,
        model_cap=cap,
        task_cap=cap,
        effective_budget=cap,
        budget_source=BudgetSource.TASK_CAP,
        budget_clamped=False,
    )

    assert budget.budget_clamped is False


def test_schema_rejects_budget_above_the_global_cap():
    with pytest.raises(ValueError):
        OutputBudget(
            global_cap=1_000,
            task_cap=2_000,
            effective_budget=2_000,
            budget_source=BudgetSource.TASK_CAP,
        )


@pytest.mark.parametrize("invalid", [0, -1])
def test_schema_rejects_non_positive_budget(invalid):
    with pytest.raises(ValueError):
        OutputBudget(
            global_cap=GLOBAL_OUTPUT_SAFETY_CAP,
            effective_budget=invalid,
            budget_source=BudgetSource.GLOBAL_CAP,
        )


def test_resolution_is_pure_and_repeatable():
    first = output_budget_service.resolve(task_type="finance_advice", model_cap=8192)
    second = output_budget_service.resolve(task_type="finance_advice", model_cap=8192)

    assert first == second


# ------------------------------------------------- consumidor não participa


def test_chat_request_has_no_token_or_budget_field():
    fields = set(ChatRequest.model_fields)

    forbidden = {
        "max_output_tokens",
        "max_tokens",
        "output_budget",
        "output_token_limit",
        "tokens",
        "generation_config",
        "transport_timeout_ms",
        "timeout",
    }
    assert fields & forbidden == set()


def test_consumer_payload_cannot_smuggle_a_budget():
    payload = ChatRequest(
        message="tentativa de burlar o orçamento",
        metadata={"max_output_tokens": 999_999},
        context={"output_budget": 999_999},
    )

    budget = output_budget_service.resolve(
        task_type="assistant_chat",
        model_cap=provider_catalog_service.max_output_tokens_for("gemini-3.5-flash"),
    )

    # A política não conhece o payload: metadata/context não têm efeito algum.
    assert budget.effective_budget == output_budget_service.task_cap("assistant_chat")
    assert payload.metadata["max_output_tokens"] == 999_999


# ------------------------------------------------------- catálogo de modelos


def test_gemini_model_declares_an_explicit_output_cap():
    cap = provider_catalog_service.max_output_tokens_for("gemini-3.5-flash")

    assert isinstance(cap, int)
    assert 0 < cap <= GLOBAL_OUTPUT_SAFETY_CAP


def test_unknown_model_has_no_declared_cap():
    assert provider_catalog_service.max_output_tokens_for("modelo-inexistente") is None
    assert provider_catalog_service.max_output_tokens_for(None) is None


# ------------------------------------------- derivação do timeout de transporte


@pytest.mark.parametrize("orchestration_seconds", [0.05, 1.0, 5.0, 30.0, 60.0, 120.0])
def test_transport_timeout_is_always_strictly_below_the_external_wait(
    orchestration_seconds,
):
    transport_ms = output_budget_service.transport_timeout_ms(orchestration_seconds)

    assert transport_ms >= 1
    assert transport_ms / 1_000 < orchestration_seconds


def test_transport_timeout_converts_seconds_to_milliseconds():
    # 30 s de espera externa → 27 s de transporte → 27000 ms, não 27.
    assert output_budget_service.transport_timeout_ms(30.0) == 27_000
    assert output_budget_service.transport_timeout_ms(60.0) == 54_000


def test_transport_timeout_keeps_a_deterministic_margin_not_a_few_milliseconds():
    orchestration_seconds = 30.0
    transport_seconds = (
        output_budget_service.transport_timeout_ms(orchestration_seconds) / 1_000
    )

    assert orchestration_seconds - transport_seconds >= 1.0


def test_transport_timeout_respects_the_ratio_ceiling_on_tiny_timeouts():
    # Nos timeouts minúsculos do clamp, a razão domina a margem fixa.
    transport_ms = output_budget_service.transport_timeout_ms(0.05)

    assert transport_ms == int(0.05 * TRANSPORT_TIMEOUT_MAX_RATIO * 1_000)
    assert MIN_TRANSPORT_TIMEOUT_SECONDS == 1.0
