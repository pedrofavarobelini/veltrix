import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.modules.chat.schemas import ChatRequest
from app.modules.orchestration.service import (
    FINANCIAL_DISCLAIMER_TEXT,
    orchestration_service,
)

client = TestClient(app)

ECOSYSTEM_TASKS = [
    "assistant_chat",
    "ecosystem_assistant",
    "finance_advice",
    "project_status",
    "report_memory_query",
    "local_model_chat",
    "evaluation_run",
]


def test_ecosystem_tasks_allowed_for_pedrocore():
    for task_type in ECOSYSTEM_TASKS:
        response = client.post(
            "/api/orchestrate",
            json={"message": "Teste", "provider": "mock", "task_type": task_type},
        )
        data = response.json()

        assert response.status_code == 200
        assert data["task_type"] == task_type
        assert data["task_allowed_for_project"] is True
        assert data["allow_real_provider"] is False


def test_finguard_is_read_only_consumer_of_assistant_tasks():
    for task_type in ("assistant_chat", "finance_advice", "project_status",
                      "report_memory_query"):
        response = client.post(
            "/api/orchestrate",
            json={
                "message": "Teste",
                "provider": "mock",
                "task_type": task_type,
                "origin_system": "finguard",
            },
        )
        data = response.json()

        assert response.status_code == 200
        assert data["task_allowed_for_project"] is True
        assert data["project_id"] == "finguard"


def test_finguard_does_not_gain_general_chat_or_ingestion():
    for task_type in ("general_chat", "report_ingestion"):
        response = client.post(
            "/api/orchestrate",
            json={
                "message": "Teste",
                "provider": "mock",
                "task_type": task_type,
                "origin_system": "finguard",
            },
        )
        data = response.json()

        assert response.status_code == 200
        assert data["task_allowed_for_project"] is False


def test_finance_advice_appends_mandatory_disclaimer():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Devo investir tudo em uma única ação?",
            "provider": "mock",
            "task_type": "finance_advice",
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert FINANCIAL_DISCLAIMER_TEXT in data["answer"]
    assert "FINANCIAL_DISCLAIMER" in data["warning_codes"]


def test_report_memory_tasks_warn_not_training():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Treine com meus relatórios.",
            "provider": "mock",
            "task_type": "report_ingestion",
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert "REPORT_MEMORY_IS_NOT_TRAINING" in data["warning_codes"]


def test_new_request_fields_default_false_and_legacy_payload_works():
    payload = ChatRequest(message="Teste")

    assert payload.allow_local_model is False
    assert payload.context_from_memory is False

    response = client.post(
        "/api/chat", json={"message": "Teste", "provider": "mock"}
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["task_warnings"] == []


def test_orchestrate_exposes_memory_used_default_false():
    response = client.post(
        "/api/orchestrate", json={"message": "Teste", "provider": "mock"}
    )
    data = response.json()

    assert response.status_code == 200
    assert data["memory_used"] is False


def test_intelligence_plan_instructions_reach_prompt_builder():
    from app.modules.prompt_builder.schemas import PromptBuildInput
    from app.modules.prompt_builder.service import prompt_builder
    from app.modules.project_context.service import project_context_resolver
    from app.modules.task_router.service import task_router
    from app.modules.intelligence_layer.service import intelligence_layer_service

    strategy = task_router.resolve("finance_advice")
    project = project_context_resolver.resolve("pedrocore")
    plan = intelligence_layer_service.build_plan(strategy=strategy, project=project)

    result = prompt_builder.build(
        PromptBuildInput(
            message="Teste",
            mode="tecnico",
            strategy=strategy,
            project=project,
            origin_system="pedrocore",
            intelligence_instructions=plan.instructions,
        )
    )

    assert "[Plano de inteligência]" in result.enriched_system_prompt
    assert "disclaimer" in result.enriched_system_prompt


def test_prompt_builder_without_plan_keeps_legacy_prompt():
    from app.modules.prompt_builder.schemas import PromptBuildInput
    from app.modules.prompt_builder.service import prompt_builder
    from app.modules.project_context.service import project_context_resolver
    from app.modules.task_router.service import task_router

    strategy = task_router.resolve("general_chat")
    project = project_context_resolver.resolve("pedrocore")

    result = prompt_builder.build(
        PromptBuildInput(
            message="Teste",
            mode="tecnico",
            strategy=strategy,
            project=project,
            origin_system="pedrocore",
        )
    )

    assert "[Plano de inteligência]" not in result.enriched_system_prompt
    assert "[Memória técnica]" not in result.enriched_system_prompt


def test_assistant_payload_projection_is_safe():
    payload = ChatRequest(
        message="Devo investir tudo?",
        provider="mock",
        task_type="finance_advice",
    )
    outcome = asyncio.run(orchestration_service.execute(payload))
    assistant = orchestration_service.build_assistant_payload(outcome)

    assert assistant.answer == outcome.answer
    assert assistant.disclaimer == FINANCIAL_DISCLAIMER_TEXT
    assert assistant.provider_used == "mock"
    assert assistant.memory_used is False
    assert assistant.evaluation is not None
    assert assistant.evaluation["passed"] is True
    assert "provider_real_blocked_by_default" in assistant.safety_flags


def test_real_provider_still_blocked_for_ecosystem_tasks():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Conselho financeiro",
            "provider": "claude",
            "task_type": "finance_advice",
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["safe_mode_blocked"] is True
    assert data["provider_used"] == "mock"
    assert "PROVIDER_REAL_BLOCKED" in data["warning_codes"]
