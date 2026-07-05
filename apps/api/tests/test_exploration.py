from fastapi.testclient import TestClient

from app.main import app
from app.modules.exploration.service import exploration_service

client = TestClient(app)


def post_exploration(
    task_type: str = "exploratory_test_plan",
    message: str = "Planejar exploração manual do fluxo de login.",
    context: dict | None = None,
):
    payload = {
        "message": message,
        "provider": "mock",
        "task_type": task_type,
        "origin_system": "pedrocore",
    }
    if context is not None:
        payload["context"] = context
    return client.post("/api/orchestrate", json=payload)


def test_exploratory_plan_created():
    response = post_exploration(
        context={"routes": ["/login", "/dashboard", "/transacoes"]}
    )
    data = response.json()

    assert response.status_code == 200
    exploration = data["exploration"]
    assert exploration is not None
    assert exploration["exploration_plan"] != []
    assert len(exploration["manual_steps"]) >= 3
    assert any("/login" in step for step in exploration["manual_steps"])
    assert exploration["required_evidence"] != []
    assert exploration["human_confirmations"] != []


def test_exploration_never_executes_actions():
    data = post_exploration().json()
    exploration = data["exploration"]

    assert exploration["can_execute_actions"] is False
    assert exploration["can_advance"] is False
    assert exploration["requires_human_review"] is True
    assert "EXPLORATION_ASSISTED_ONLY" in data["warning_codes"]
    assert "HUMAN_CONFIRMATION_REQUIRED" in data["warning_codes"]
    assert "EXPLORATION_CANNOT_EXECUTE_COMMANDS" in data["warning_codes"]


def test_exploration_blocks_destructive_request():
    data = post_exploration(
        message="Explorar o sistema e deletar os registros de teste antigos."
    ).json()

    assert "EXPLORATION_ACTION_BLOCKED" in data["warning_codes"]
    assert data["exploration"]["can_execute_actions"] is False


def test_exploration_lists_blocked_actions():
    data = post_exploration().json()
    blocked = data["exploration"]["blocked_actions"]

    assert any("Playwright" in action for action in blocked)
    assert any("navegador" in action.lower() for action in blocked)
    assert any("FinGuard" in action for action in blocked)
    assert any("comandos" in action.lower() for action in blocked)


def test_exploration_identifies_risk_areas():
    data = post_exploration(
        message="Explorar fluxo de pagamento e login.",
        context={"routes": ["/pagamentos"]},
    ).json()
    risks = data["exploration"]["risk_areas"]

    assert any("financeiro" in risk.lower() or "pagamento" in risk.lower() for risk in risks)
    assert any("login" in risk.lower() or "autentica" in risk.lower() for risk in risks)


def test_all_exploration_task_types_supported():
    for task_type in (
        "exploratory_test_plan",
        "manual_exploration_report",
        "assisted_exploration_review",
    ):
        response = post_exploration(task_type=task_type)
        data = response.json()

        assert response.status_code == 200, f"task: {task_type}"
        assert data["exploration"] is not None, f"task: {task_type}"
        assert data["task_type"] == task_type
        assert data["task_allowed_for_project"] is True


def test_non_exploration_task_has_no_exploration():
    response = client.post(
        "/api/orchestrate",
        json={"message": "Oi", "provider": "mock", "task_type": "general_chat"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["exploration"] is None


def test_exploration_service_returns_none_for_other_tasks():
    assert exploration_service.build("general_chat", "x") is None
    assert exploration_service.build("qa_report_analysis", "x") is None


def test_release_gate_not_advanced_by_exploration_plan_alone():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Pode avançar com base no plano exploratório?",
            "provider": "local_qa",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "artifacts": [
                {
                    "type": "text",
                    "name": "plano.txt",
                    "content": "Plano exploratório: passo 1 abrir tela, passo 2 conferir.",
                }
            ],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["release_gate"]["can_advance"] is False


def test_exploration_does_not_call_real_provider():
    data = post_exploration().json()

    assert data["provider_used"] in {"mock", "local_qa"}
    assert data["safe_mode_blocked"] is False
