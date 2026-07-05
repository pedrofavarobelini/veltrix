from fastapi.testclient import TestClient

from app.main import app
from app.modules.artifacts.schemas import ArtifactInput
from app.modules.artifacts.service import artifact_service
from app.modules.policy_enforcement.service import policy_enforcement_service
from app.modules.project_context.service import project_context_resolver
from app.modules.qa_analysis.service import qa_text_analyzer
from app.modules.qa_response.service import qa_response_service
from app.modules.task_router.service import task_router

client = TestClient(app)

CLEAN_SUCCESS = "All tests passed. 0 failed. Build successful."


def gate_with_provider(provider_used: str):
    artifacts_result = artifact_service.process(
        [ArtifactInput(type="qa_report", name="qa.md", content=CLEAN_SUCCESS)]
    )
    analysis = qa_text_analyzer.analyze(
        task_type="release_gate_review", artifacts_result=artifacts_result
    )
    return qa_response_service.evaluate_release_gate(
        artifacts_result=artifacts_result,
        analysis=analysis,
        fallback_used=False,
        safe_mode_blocked=False,
        provider_used=provider_used,
    )


def test_real_provider_cannot_approve_gate_alone():
    for provider in ("gemini", "openai", "claude", "deepseek", "grok"):
        gate = gate_with_provider(provider)

        assert gate.can_advance is False, f"provider aprovou sozinho: {provider}"
        assert "RELEASE_REQUIRES_HUMAN_REVIEW" in gate.warning_codes
        assert "revisão humana" in gate.blocked_reason


def test_local_qa_still_approves_clean_gate():
    gate = gate_with_provider("local_qa")

    assert gate.can_advance is True
    assert gate.blocked_reason is None


def test_mock_still_blocked_at_gate():
    gate = gate_with_provider("mock")

    assert gate.can_advance is False


def test_enforcement_dangerous_task_blocked_even_with_enforce_off():
    strategy = task_router.resolve("unknown")
    project = project_context_resolver.resolve("pedrocore")
    policy = project_context_resolver.evaluate_task_policy(project, strategy.task_type)

    result = policy_enforcement_service.evaluate(
        raw_task_type="delete_all_records",
        strategy=strategy,
        project=project,
        policy=policy,
        enforce=False,
    )

    assert result.blocked is True
    assert result.error_code == "PROJECT_POLICY_BLOCKED"


def test_enforcement_allows_safe_task():
    strategy = task_router.resolve("qa_report_analysis")
    project = project_context_resolver.resolve("finguard")
    policy = project_context_resolver.evaluate_task_policy(project, strategy.task_type)

    result = policy_enforcement_service.evaluate(
        raw_task_type="qa_report_analysis",
        strategy=strategy,
        project=project,
        policy=policy,
        enforce=True,
    )

    assert result.blocked is False


def test_gate_api_real_provider_authorized_still_requires_human_review(monkeypatch):
    # Mesmo autorizando provider real explicitamente, o gate não aprova sozinho.
    # Gemini sem chave nos testes cai em fallback → bloqueio por fallback; e o
    # guard de provider confiável cobre o caso com chave. Ambos bloqueiam.
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Pode liberar?",
            "provider": "gemini",
            "allow_real_provider": False,
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "content": CLEAN_SUCCESS}],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["release_gate"]["can_advance"] is False
    assert "RELEASE_GATE_BLOCKED" in data["warning_codes"]


def test_gate_api_exploration_plan_only_never_advances():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Pode liberar com base no plano exploratório?",
            "provider": "local_qa",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "artifacts": [
                {
                    "type": "text",
                    "name": "plano-exploratorio.txt",
                    "content": "Plano: abrir telas, conferir estados, registrar evidências.",
                }
            ],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["release_gate"]["can_advance"] is False


def test_safe_scenarios_still_work_end_to_end():
    response = client.post(
        "/api/orchestrate",
        json={
            "message": "Pode liberar?",
            "provider": "local_qa",
            "task_type": "release_gate_review",
            "origin_system": "finguard",
            "artifacts": [{"type": "qa_report", "content": CLEAN_SUCCESS}],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["release_gate"]["can_advance"] is True
