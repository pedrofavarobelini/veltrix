import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.modules.chat.schemas import ChatRequest
from app.modules.intelligence_layer.schemas import (
    IntelligenceContextPolicy,
    IntelligencePlan,
)
from app.modules.intelligence_layer.service import (
    SAFETY_FLAG_HUMAN_REVIEW,
    SAFETY_FLAG_REAL_PROVIDER_BLOCKED,
    intelligence_layer_service,
)
from app.modules.orchestration.service import orchestration_service
from app.modules.project_context.service import project_context_resolver
from app.modules.task_router.service import _STRATEGIES, task_router

client = TestClient(app)


def _plan_for(task_type: str, origin_system: str = "pedrocore") -> IntelligencePlan:
    strategy = task_router.resolve(task_type)
    project = project_context_resolver.resolve(origin_system)
    return intelligence_layer_service.build_plan(strategy=strategy, project=project)


def test_general_chat_uses_general_assistant_profile():
    plan = _plan_for("general_chat")

    assert plan.task_type == "general_chat"
    assert plan.response_profile in {"general_assistant", "technical_direct"}
    assert plan.context_policy.requires_human_review is False


def test_technical_explanation_uses_technical_direct_profile():
    plan = _plan_for("technical_explanation")

    assert plan.response_profile == "technical_direct"


def test_qa_report_analysis_uses_qa_strict_profile():
    plan = _plan_for("qa_report_analysis")

    assert plan.response_profile == "qa_strict"
    assert plan.context_policy.requires_human_review is True
    assert plan.evaluation_hints != []


def test_release_gate_review_is_strict_and_requires_human_review():
    plan = _plan_for("release_gate_review")

    assert plan.response_profile == "release_gate_strict"
    assert plan.context_policy.requires_human_review is True
    assert SAFETY_FLAG_HUMAN_REVIEW in plan.safety_flags
    assert any("release gate" in i.lower() for i in plan.instructions)


def test_no_plan_enables_real_provider_for_any_known_task():
    for task_type in _STRATEGIES:
        plan = _plan_for(task_type)

        assert plan.context_policy.allow_real_provider is False
        assert SAFETY_FLAG_REAL_PROVIDER_BLOCKED in plan.safety_flags


def test_context_policy_rejects_real_provider_enabled():
    with pytest.raises(ValidationError):
        IntelligenceContextPolicy(allow_real_provider=True)


def test_critical_task_gets_safety_and_evaluation_hints():
    plan = _plan_for("release_gate_review")

    assert len(plan.safety_flags) >= 2
    assert any("revisão humana" in hint for hint in plan.evaluation_hints)


def test_plan_never_persists_memory_context_by_default():
    for task_type in _STRATEGIES:
        plan = _plan_for(task_type)

        assert plan.context_policy.allow_memory_context is False


def test_orchestration_outcome_carries_internal_intelligence_plan():
    payload = ChatRequest(message="Explique o pipeline", provider="mock")
    outcome = asyncio.run(orchestration_service.execute(payload))

    assert outcome.intelligence_plan is not None
    assert outcome.intelligence_plan.task_type == "general_chat"
    assert outcome.intelligence_plan.context_policy.allow_real_provider is False


def test_new_foundation_task_types_are_allowed_for_pedrocore():
    for task_type in (
        "report_ingestion",
        "project_memory_summary",
        "model_foundation_review",
        "intelligence_planning",
    ):
        response = client.post(
            "/api/chat",
            json={
                "message": "Planejamento de fundação",
                "mode": "tecnico",
                "provider": "mock",
                "task_type": task_type,
            },
        )

        data = response.json()

        assert response.status_code == 200
        assert data["task_type"] == task_type
        assert data["task_criticality"] == "medium"
        assert not any(
            "não listado em allowed_tasks" in w for w in data["task_warnings"]
        )


def test_new_foundation_task_types_are_not_allowed_for_finguard():
    response = client.post(
        "/api/chat",
        json={
            "message": "Ingestão de relatório",
            "mode": "tecnico",
            "provider": "mock",
            "task_type": "report_ingestion",
            "origin_system": "finguard",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert any("não listado em allowed_tasks" in w for w in data["task_warnings"])


def test_orchestrate_response_contract_unchanged_by_intelligence_plan():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Teste de contrato",
            "mode": "tecnico",
            "provider": "mock",
        },
    )

    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["allow_real_provider"] is False
    assert "intelligence_plan" not in data
