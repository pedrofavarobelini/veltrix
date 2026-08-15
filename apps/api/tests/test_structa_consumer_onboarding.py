"""Onboarding offline e fail-closed do consumer Structa.

Nenhum teste deste modulo chama adapter externo. A autorizacao positiva para
Gemini termina no avaliador local; os fluxos HTTP exercitados sao somente
bloqueios anteriores ao provider ou o safe mode default-off.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.caller_identity.schemas import CallerRole, IdentityStrength
from app.modules.caller_identity.service import (
    FLAG_CALLER_REGISTRY,
    FLAG_INTERNAL_API_KEY,
    caller_identity_service,
)
from app.modules.chat.schemas import ChatRequest
from app.modules.contracts import codes
from app.modules.orchestration.service import orchestration_service
from app.modules.provider_authorization.schemas import AuthorizationResult
from app.modules.provider_authorization.service import provider_authorization_service
from app.modules.provider_catalog.schemas import HomologationStatus
from app.modules.provider_catalog.service import provider_catalog_service
from app.modules.project_context.service import project_context_resolver


client = TestClient(app)
AUTH_HEADER = "X-PedroCore-Api-Key"
STRUCTA_CREDENTIAL = "structa-credential-for-offline-tests-only"
STRUCTA_COMMON_CREDENTIAL = "structa-common-role-offline-tests-only"


@pytest.fixture
def structa_registry(monkeypatch):
    registry = [
        {
            "credential_id": "structa-report-intelligence-test",
            "api_key": STRUCTA_CREDENTIAL,
            "project_id": "structa",
            "role": "technical_tool",
            "environment": "development",
            "allowed_origins": ["structa"],
        },
        {
            "credential_id": "structa-common-role-test",
            "api_key": STRUCTA_COMMON_CREDENTIAL,
            "project_id": "structa",
            "role": "common_consumer",
            "environment": "development",
            "allowed_origins": ["structa"],
        },
    ]
    monkeypatch.setenv(FLAG_CALLER_REGISTRY, json.dumps(registry))
    monkeypatch.delenv(FLAG_INTERNAL_API_KEY, raising=False)
    monkeypatch.delenv("PEDROCORE_REAL_FALLBACK_ENABLED", raising=False)
    monkeypatch.setattr(settings, "gemini_api_key", "configured-only-for-offline-test")
    return registry


def _structa_context(credential: str = STRUCTA_CREDENTIAL):
    resolution = caller_identity_service.resolve(credential)
    assert resolution.rejected is False
    project = project_context_resolver.resolve("Structa")
    claim = caller_identity_service.validate_origin_claim(
        resolution.context, "Structa", project.project_id
    )
    assert claim.rejected is False
    return resolution.context, project, claim


def _post(credential: str | None, **overrides):
    payload = {
        "message": "Contrato sintetico de Report Intelligence.",
        "provider": "gemini",
        "task_type": "qa_report_analysis",
        "origin_system": "Structa",
        "allow_real_provider": False,
    }
    payload.update(overrides)
    headers = {AUTH_HEADER: credential} if credential else {}
    return client.post("/api/orchestrate", json=payload, headers=headers)


def test_structa_project_context_is_exact_and_report_only():
    canonical = project_context_resolver.resolve("Structa")
    lowercase = project_context_resolver.resolve("structa")
    lookalike = project_context_resolver.resolve("StructaXYZ")

    assert canonical.project_id == lowercase.project_id == "structa"
    assert canonical.display_name == "Structa"
    assert canonical.allowed_tasks == ["qa_report_analysis"]
    assert canonical.read_only is True
    assert canonical.can_execute_commands is False
    assert canonical.can_write_files is False
    assert lookalike.project_id == "unknown"


def test_structa_registered_identity_is_project_bound(structa_registry):
    caller, project, claim = _structa_context()

    assert project.project_id == "structa"
    assert caller.project_id == "structa"
    assert caller.caller_role is CallerRole.TECHNICAL_TOOL
    assert caller.identity_strength is IdentityStrength.REGISTERED
    assert caller.authenticated is True
    assert claim.identity_project_id == "structa"
    assert claim.context_project_id == "structa"


def test_structa_gemini_is_authorized_only_in_local_evaluator(structa_registry):
    caller, project, claim = _structa_context()
    policy = project_context_resolver.evaluate_task_policy(
        project, "qa_report_analysis"
    )
    definition = provider_catalog_service.get("gemini")
    decision = provider_authorization_service.evaluate(
        identity_strength=caller.identity_strength,
        project_id=claim.identity_project_id,
        caller_role=caller.caller_role,
        environment=caller.environment,
        provider_id="gemini",
    )

    assert policy.allowed is True
    assert definition is not None
    assert definition.configured is True
    assert definition.homologation is HomologationStatus.HOMOLOGATED_REAL
    assert decision.result is AuthorizationResult.ALLOWED
    assert orchestration_service._real_fallback_enabled() is False


def test_structa_without_explicit_real_opt_in_never_calls_provider(
    structa_registry, real_provider_guard
):
    response = _post(STRUCTA_CREDENTIAL, allow_real_provider=False)
    data = response.json()

    assert response.status_code == 200
    assert data["safe_mode_blocked"] is True
    assert data["provider_used"] == "mock"
    assert data["fallback_used"] is True
    assert codes.PROVIDER_REAL_BLOCKED in data["warning_codes"]
    assert real_provider_guard == []


def test_structa_missing_and_unknown_credentials_are_denied_before_provider(
    structa_registry, real_provider_guard
):
    missing = _post(None)
    unknown = _post("unknown-structa-credential")

    assert missing.status_code == 401
    assert missing.json()["error_code"] == codes.CALLER_CREDENTIAL_MISSING
    assert unknown.status_code == 401
    assert unknown.json()["error_code"] == codes.CALLER_CREDENTIAL_UNKNOWN
    assert real_provider_guard == []


def test_structa_origin_mismatch_is_denied_before_provider(
    structa_registry, real_provider_guard
):
    response = _post(STRUCTA_CREDENTIAL, origin_system="finguard")
    data = response.json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.CALLER_ORIGIN_MISMATCH
    assert data["provider_used"] == "none"
    assert real_provider_guard == []


def test_structa_inadequate_role_is_denied(structa_registry):
    caller, _, claim = _structa_context(STRUCTA_COMMON_CREDENTIAL)
    decision = provider_authorization_service.evaluate(
        identity_strength=caller.identity_strength,
        project_id=claim.identity_project_id,
        caller_role=caller.caller_role,
        environment=caller.environment,
        provider_id="gemini",
    )

    assert caller.caller_role is CallerRole.COMMON_CONSUMER
    assert decision.denied is True
    assert decision.error_code == codes.PROVIDER_NOT_AUTHORIZED_FOR_PROJECT


@pytest.mark.parametrize("provider_id", ["openai", "claude", "deepseek", "grok"])
def test_structa_non_gemini_providers_are_denied(structa_registry, provider_id):
    caller, _, claim = _structa_context()
    decision = provider_authorization_service.evaluate(
        identity_strength=caller.identity_strength,
        project_id=claim.identity_project_id,
        caller_role=caller.caller_role,
        environment=caller.environment,
        provider_id=provider_id,
    )

    assert decision.denied is True


def test_structa_unlisted_critical_task_is_blocked_before_provider(
    structa_registry, real_provider_guard
):
    response = _post(
        STRUCTA_CREDENTIAL,
        task_type="qa_failure_diagnosis",
        allow_real_provider=True,
    )
    data = response.json()

    assert data["status"] == "blocked"
    assert data["error_code"] == codes.PROJECT_POLICY_BLOCKED
    assert data["provider_used"] == "none"
    assert data["fallback_used"] is False
    assert real_provider_guard == []


def test_unknown_project_and_local_unregistered_structa_remain_denied(
    structa_registry
):
    for identity_strength, project_id in (
        (IdentityStrength.REGISTERED, "unknown"),
        (IdentityStrength.LOCAL_TRUSTED, "structa"),
    ):
        decision = provider_authorization_service.evaluate(
            identity_strength=identity_strength,
            project_id=project_id,
            caller_role=CallerRole.TECHNICAL_TOOL,
            environment="development",
            provider_id="gemini",
        )
        assert decision.denied is True


def test_finguard_and_pedrocore_authorization_rules_are_preserved(
    structa_registry
):
    finguard = provider_authorization_service.evaluate(
        identity_strength=IdentityStrength.REGISTERED,
        project_id="finguard",
        caller_role=CallerRole.COMMON_CONSUMER,
        environment="development",
        provider_id="gemini",
    )
    pedrocore = provider_authorization_service.evaluate(
        identity_strength=IdentityStrength.LOCAL_TRUSTED,
        project_id="pedrocore",
        caller_role=CallerRole.TECHNICAL_TOOL,
        environment="development",
        provider_id="gemini",
    )

    assert finguard.result is AuthorizationResult.ALLOWED
    assert pedrocore.result is AuthorizationResult.ALLOWED


def test_real_provider_and_fallback_defaults_remain_off(structa_registry):
    request = ChatRequest(message="Contrato sintetico")

    assert request.allow_real_provider is False
    assert orchestration_service._real_fallback_enabled() is False
