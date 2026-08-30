"""Contract tests dos Universal Contracts V1.

ADR-PEDROCORE-UNIVERSAL-CONTRACTS-01.

O que estes testes protegem
---------------------------

Um contrato de integracao so vale enquanto o servidor recusa o que prometeu
recusar. A maior parte destes testes, por isso, nao verifica que o caminho
feliz funciona — verifica que o caminho DESONESTO falha: consumidor declarando
elegibilidade, fabricando autorizacao, ligando coleta automatica, mentindo o
projeto ou enviando um Training Candidate pronto.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.modules.project_context.manifests import (
    PROJECT_MANIFESTS,
    has_trait,
    manifest_for,
    protected_resource_markers,
)
from app.modules.universal_contracts.authority import (
    reserved_field_names,
    scan_for_reserved_authority,
)
from app.modules.universal_contracts.capability_manifest import (
    CapabilityDeclaration,
    ProducerTrait,
    ProjectCapability,
    ProjectCapabilityManifestV1,
)
from app.modules.universal_contracts.envelope import PedroCoreIntegrationEnvelopeV1
from app.modules.universal_contracts.execution_outcome import (
    ExecutionOutcomeV1,
    ExecutionResult,
)
from app.modules.universal_contracts.learning_source import (
    LearningSourceKind,
    LearningSourceV1,
)
from app.modules.universal_contracts.quality_evidence import (
    EvidenceOutcome,
    QualityEvidenceV1,
    SuiteObservation,
)
from app.modules.universal_contracts.service import (
    CONTRACT_AUTHORITY_VIOLATION,
    CONTRACT_CAPABILITY_NOT_DECLARED,
    CONTRACT_CAPABILITY_VERSION_UNSUPPORTED,
    CONTRACT_MANIFEST_MISSING,
    CONTRACT_PAYLOAD_INVALID,
    CONTRACT_PRODUCER_BINDING_MISMATCH,
    CONTRACT_PROJECT_BINDING_MISMATCH,
    CONTRACT_VERSION_UNKNOWN,
    universal_contract_service,
)
from app.modules.universal_contracts.versioning import (
    CAPABILITY_MANIFEST_V1,
    EXECUTION_OUTCOME_V1,
    INTEGRATION_ENVELOPE_V1,
    LEARNING_SOURCE_V1,
    QUALITY_EVIDENCE_V1,
    ContractVersionStatus,
    is_supported,
    version_status,
)

NOW = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)


def _manifest(
    *capabilities: CapabilityDeclaration,
    project_id: str = "demo",
    traits: frozenset[ProducerTrait] = frozenset(),
) -> ProjectCapabilityManifestV1:
    return ProjectCapabilityManifestV1(
        project_id=project_id,
        display_name="Demo",
        producer_id="demo-ci",
        capabilities=tuple(capabilities),
        traits=traits,
    )


def _quality_payload(**overrides) -> dict:
    payload = {
        "evidence_id": "ev-1",
        "outcome": "passed",
        "environment": "ci",
        "observed_at": NOW.isoformat(),
        "suites": [
            {"suite_id": "unit", "outcome": "passed", "total": 12, "passed": 12}
        ],
    }
    payload.update(overrides)
    return payload


def _envelope(payload: dict, payload_type: str = "quality_evidence", **overrides) -> dict:
    envelope = {
        "envelope_version": INTEGRATION_ENVELOPE_V1,
        "event_id": "evt-1",
        "payload_type": payload_type,
        "project_id": "demo",
        "producer_id": "demo-ci",
        "submitted_at": NOW.isoformat(),
        "payload": payload,
    }
    envelope.update(overrides)
    return envelope


def _validate(envelope: object, manifest: ProjectCapabilityManifestV1 | None):
    return universal_contract_service.validate_envelope(
        envelope,
        authenticated_project_id="demo",
        authenticated_producer_id="demo-ci",
        manifest=manifest,
    )


# ---------------------------------------------------------------------------
# Project Capability Manifest V1
# ---------------------------------------------------------------------------


def test_manifest_is_valid_and_declares_its_version():
    manifest = _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.QUALITY_EVIDENCE,
            contract_versions=(QUALITY_EVIDENCE_V1,),
        )
    )
    assert manifest.manifest_version == CAPABILITY_MANIFEST_V1
    assert manifest.declares(ProjectCapability.QUALITY_EVIDENCE)
    assert manifest.supports_contract(ProjectCapability.QUALITY_EVIDENCE, QUALITY_EVIDENCE_V1)


def test_manifest_rejects_unknown_capability():
    """Capability desconhecida e recusada, nao ignorada.

    Ignorar ensinaria o integrador que ele negociou algo que o servidor nunca
    entendeu — e a proxima versao dele passaria a depender disso.
    """
    with pytest.raises(ValidationError):
        ProjectCapabilityManifestV1(
            project_id="demo",
            display_name="Demo",
            capabilities=({"capability": "teleportation", "contract_versions": ()},),
        )


def test_manifest_rejects_unknown_contract_version():
    with pytest.raises(ValidationError) as error:
        CapabilityDeclaration(
            capability=ProjectCapability.LEARNING_SOURCE,
            contract_versions=("pedrocore-learning-source/v9",),
        )
    assert "desconhecidas" in str(error.value)


def test_manifest_rejects_duplicated_capability():
    with pytest.raises(ValidationError) as error:
        _manifest(
            CapabilityDeclaration(capability=ProjectCapability.ASSISTANT),
            CapabilityDeclaration(capability=ProjectCapability.ASSISTANT),
        )
    assert "duplicidade" in str(error.value)


def test_manifest_rejects_invalid_project_identity():
    with pytest.raises(ValidationError):
        ProjectCapabilityManifestV1(project_id="", display_name="Demo")


def test_missing_capability_blocks_the_submission():
    manifest = _manifest(CapabilityDeclaration(capability=ProjectCapability.ASSISTANT))
    result = _validate(_envelope(_quality_payload()), manifest)
    assert not result.accepted
    assert result.error_code == CONTRACT_CAPABILITY_NOT_DECLARED


def test_capability_declared_without_the_contract_version_is_rejected():
    manifest = _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.QUALITY_EVIDENCE,
            contract_versions=(EXECUTION_OUTCOME_V1,),
        )
    )
    result = _validate(_envelope(_quality_payload()), manifest)
    assert not result.accepted
    assert result.error_code == CONTRACT_CAPABILITY_VERSION_UNSUPPORTED


def test_manifest_never_grants_training_authorization():
    """O manifesto descreve capacidade; ele nao autoriza treino.

    Nao existe campo de autorizacao aqui — e a ausencia e o mecanismo. Se um dia
    alguem acrescentar um, este teste falha e a discussao acontece antes do
    merge, e nao depois de um dataset.
    """
    manifest = _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.LEARNING_SOURCE,
            contract_versions=(LEARNING_SOURCE_V1,),
        )
    )
    fields = set(manifest.model_dump().keys())
    forbidden = {
        "authorized",
        "authorization",
        "allows_neural_training",
        "training_authorization",
        "eligibility",
    }
    assert not (fields & forbidden)


def test_registered_manifests_are_internally_consistent():
    for project_id, manifest in PROJECT_MANIFESTS.items():
        assert manifest.project_id == project_id
        assert manifest_for(project_id) is manifest
        assert manifest_for(project_id.upper()) is manifest


def test_unregistered_project_has_no_manifest_and_no_capability():
    assert manifest_for("projeto-inexistente") is None
    assert not has_trait("projeto-inexistente", ProducerTrait.IDEMPOTENT_SUBMISSION)
    assert manifest_for(None) is None
    assert manifest_for("") is None


# ---------------------------------------------------------------------------
# Quality Evidence Contract V1
# ---------------------------------------------------------------------------


def test_valid_quality_evidence_is_accepted():
    manifest = _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.QUALITY_EVIDENCE,
            contract_versions=(QUALITY_EVIDENCE_V1,),
        )
    )
    result = _validate(_envelope(_quality_payload()), manifest)
    assert result.accepted, result.reason
    assert result.envelope is not None
    assert result.envelope.payload.total_observed_cases() == 12


def test_quality_evidence_rejects_inconsistent_counts():
    """10 totais com 7+2+2 nao e relatorio ruim: e relatorio impossivel."""
    with pytest.raises(ValidationError) as error:
        SuiteObservation(
            suite_id="unit", outcome=EvidenceOutcome.PASSED, total=10, passed=7,
            failed=2, skipped=2,
        )
    assert "inconsistentes" in str(error.value)


def test_quality_evidence_rejects_passed_suite_that_reports_failures():
    with pytest.raises(ValidationError):
        SuiteObservation(
            suite_id="unit", outcome=EvidenceOutcome.PASSED, total=2, passed=1, failed=1
        )


def test_quality_evidence_rejects_global_pass_contradicting_a_failing_suite():
    """Enterrar a falha na suite e anunciar sucesso no topo e julgamento, nao fato."""
    with pytest.raises(ValidationError) as error:
        QualityEvidenceV1(
            evidence_id="ev-1",
            outcome=EvidenceOutcome.PASSED,
            environment="ci",
            observed_at=NOW,
            suites=(
                SuiteObservation(
                    suite_id="unit", outcome=EvidenceOutcome.FAILED, total=2,
                    passed=1, failed=1,
                ),
            ),
        )
    assert "contradiz" in str(error.value)


def test_quality_evidence_requires_timezone_aware_timestamp():
    with pytest.raises(ValidationError) as error:
        QualityEvidenceV1(
            evidence_id="ev-1",
            outcome=EvidenceOutcome.PASSED,
            environment="ci",
            observed_at=datetime(2026, 8, 29, 12, 0, 0),
        )
    assert "timezone" in str(error.value)


def test_quality_evidence_has_no_authoritative_score_field():
    """QEC transporta fato observavel; score autoritativo nao existe aqui."""
    fields = set(QualityEvidenceV1.model_fields)
    assert "quality_score" not in fields
    assert "eligibility" not in fields
    assert "approved" not in fields


def test_quality_evidence_rejects_client_supplied_quality_score():
    manifest = _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.QUALITY_EVIDENCE,
            contract_versions=(QUALITY_EVIDENCE_V1,),
        )
    )
    payload = _quality_payload(quality_score=100)
    result = _validate(_envelope(payload), manifest)
    assert not result.accepted
    assert result.error_code == CONTRACT_AUTHORITY_VIOLATION


def test_quality_evidence_rejects_malformed_payload():
    manifest = _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.QUALITY_EVIDENCE,
            contract_versions=(QUALITY_EVIDENCE_V1,),
        )
    )
    result = _validate(_envelope({"evidence_id": "ev-1"}), manifest)
    assert not result.accepted
    assert result.error_code == CONTRACT_PAYLOAD_INVALID


# ---------------------------------------------------------------------------
# Execution Outcome Contract V1
# ---------------------------------------------------------------------------


def _execution_payload(**overrides) -> dict:
    payload = {
        "outcome_id": "run-1",
        "operation": "deploy",
        "result": "succeeded",
        "final_state": "stable",
        "started_at": NOW.isoformat(),
        "finished_at": (NOW + timedelta(seconds=30)).isoformat(),
    }
    payload.update(overrides)
    return payload


def test_valid_execution_outcome_is_accepted():
    manifest = _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.EXECUTION_OUTCOME,
            contract_versions=(EXECUTION_OUTCOME_V1,),
        )
    )
    result = _validate(
        _envelope(_execution_payload(), payload_type="execution_outcome"), manifest
    )
    assert result.accepted, result.reason
    assert result.envelope.payload.duration_ms() == 30_000.0


def test_execution_outcome_rejects_invalid_result():
    with pytest.raises(ValidationError):
        ExecutionOutcomeV1(
            outcome_id="run-1", operation="deploy", result="mostly_fine",
            started_at=NOW, finished_at=NOW,
        )


def test_execution_outcome_rejects_impossible_timestamps():
    with pytest.raises(ValidationError) as error:
        ExecutionOutcomeV1(
            outcome_id="run-1", operation="deploy", result=ExecutionResult.SUCCEEDED,
            started_at=NOW, finished_at=NOW - timedelta(seconds=1),
        )
    assert "anterior" in str(error.value)


def test_execution_outcome_failure_requires_a_diagnostic():
    """Falha sem diagnostico e um resultado que ninguem pode investigar."""
    with pytest.raises(ValidationError) as error:
        ExecutionOutcomeV1(
            outcome_id="run-1", operation="deploy", result=ExecutionResult.FAILED,
            started_at=NOW, finished_at=NOW,
        )
    assert "diagnostico" in str(error.value)


def test_execution_outcome_rejects_divergent_project():
    manifest = _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.EXECUTION_OUTCOME,
            contract_versions=(EXECUTION_OUTCOME_V1,),
        )
    )
    envelope = _envelope(
        _execution_payload(), payload_type="execution_outcome", project_id="outro"
    )
    result = _validate(envelope, manifest)
    assert not result.accepted
    assert result.error_code == CONTRACT_PROJECT_BINDING_MISMATCH


def test_execution_outcome_rejects_divergent_producer():
    manifest = _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.EXECUTION_OUTCOME,
            contract_versions=(EXECUTION_OUTCOME_V1,),
        )
    )
    envelope = _envelope(
        _execution_payload(), payload_type="execution_outcome", producer_id="outro-ci"
    )
    result = _validate(envelope, manifest)
    assert not result.accepted
    assert result.error_code == CONTRACT_PRODUCER_BINDING_MISMATCH


def test_execution_outcome_carries_correlation():
    manifest = _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.EXECUTION_OUTCOME,
            contract_versions=(EXECUTION_OUTCOME_V1,),
        )
    )
    envelope = _envelope(
        _execution_payload(), payload_type="execution_outcome", correlation_id="corr-9"
    )
    result = _validate(envelope, manifest)
    assert result.accepted
    assert result.envelope.correlation_id == "corr-9"


def test_execution_outcome_cannot_become_a_training_candidate():
    """Um resultado de execucao e fonte operacional, nunca exemplo de treino."""
    fields = set(ExecutionOutcomeV1.model_fields)
    assert "training_purpose" not in fields
    assert "candidate_id" not in fields
    assert "eligibility" not in fields


# ---------------------------------------------------------------------------
# Learning Source Contract V1
# ---------------------------------------------------------------------------


def _learning_payload(**overrides) -> dict:
    payload = {
        "source_id": "src-1",
        "provenance": {
            "source_kind": "execution_outcome",
            "source_schema_version": "run/v1",
            "producer_policy_version": "demo-policy/v1",
            "produced_at": NOW.isoformat(),
            "content_signature": "sha256:" + "a" * 64,
        },
        "producer_asserted_outcome": "successful",
        "derived_features": {"duration_ms": 1200, "retries": 0},
    }
    payload.update(overrides)
    return payload


def _learning_manifest() -> ProjectCapabilityManifestV1:
    return _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.LEARNING_SOURCE,
            contract_versions=(LEARNING_SOURCE_V1,),
        )
    )


def test_valid_learning_source_is_accepted_without_becoming_a_candidate():
    """Aceitar a fonte NAO cria candidato — e a distincao que a Era protege."""
    result = _validate(
        _envelope(_learning_payload(), payload_type="learning_source"),
        _learning_manifest(),
    )
    assert result.accepted, result.reason
    assert result.training_candidate_created is False
    assert result.automatic_collection_performed is False


def test_learning_source_requires_minimum_provenance():
    result = _validate(
        _envelope(
            _learning_payload(provenance={"source_kind": "execution_outcome"}),
            payload_type="learning_source",
        ),
        _learning_manifest(),
    )
    assert not result.accepted
    assert result.error_code == CONTRACT_PAYLOAD_INVALID


def test_learning_source_rejects_meaningless_policy_version():
    """"unknown" e pior que ausente: parece preenchido e nao reconstroi nada."""
    payload = _learning_payload()
    payload["provenance"] = dict(payload["provenance"])
    payload["provenance"]["producer_policy_version"] = "unknown"
    result = _validate(
        _envelope(payload, payload_type="learning_source"), _learning_manifest()
    )
    assert not result.accepted
    assert result.error_code == CONTRACT_PAYLOAD_INVALID


def test_learning_source_rejects_a_finished_training_candidate():
    """A tentativa mais perigosa: o consumidor entregando o objeto interno pronto."""
    payload = _learning_payload(training_candidate={"candidate_id": "x", "target": {}})
    result = _validate(
        _envelope(payload, payload_type="learning_source"), _learning_manifest()
    )
    assert not result.accepted
    assert result.error_code == CONTRACT_AUTHORITY_VIOLATION


def test_learning_source_rejects_attempt_to_enable_automatic_collection():
    payload = _learning_payload(automatic_collection=True)
    result = _validate(
        _envelope(payload, payload_type="learning_source"), _learning_manifest()
    )
    assert not result.accepted
    assert result.error_code == CONTRACT_AUTHORITY_VIOLATION


def test_learning_source_rejects_declared_final_eligibility():
    payload = _learning_payload(eligibility="eligible")
    result = _validate(
        _envelope(payload, payload_type="learning_source"), _learning_manifest()
    )
    assert not result.accepted
    assert result.error_code == CONTRACT_AUTHORITY_VIOLATION


def test_learning_source_rejects_fabricated_authorization():
    payload = _learning_payload(
        data_use_authorization={"authorized": True, "allows_neural_training": True}
    )
    result = _validate(
        _envelope(payload, payload_type="learning_source"), _learning_manifest()
    )
    assert not result.accepted
    assert result.error_code == CONTRACT_AUTHORITY_VIOLATION


def test_learning_source_rejects_raw_content_flag():
    """`derived_content_only` e tipo, nao flag: `False` nem chega a ser regra."""
    with pytest.raises(ValidationError):
        LearningSourceV1.model_validate(_learning_payload(derived_content_only=False))


def test_learning_source_requires_consent_for_person_derived_sources():
    payload = _learning_payload()
    payload["provenance"] = dict(payload["provenance"])
    payload["provenance"]["source_kind"] = LearningSourceKind.REPORT_SNAPSHOT.value
    with pytest.raises(ValidationError) as error:
        LearningSourceV1.model_validate(payload)
    assert "training_consent" in str(error.value)


def test_learning_source_refuses_free_text_in_derived_features():
    """"Derivado" nao pode virar o lugar onde conteudo bruto cabe."""
    with pytest.raises(ValidationError) as error:
        LearningSourceV1.model_validate(
            _learning_payload(derived_features={"journal": "x" * 300})
        )
    assert "256" in str(error.value)


def test_learning_source_has_no_internal_governance_fields():
    fields = set(LearningSourceV1.model_fields)
    forbidden = {
        "eligibility", "authorized", "candidate_id", "lifecycle",
        "training_purpose", "quality_score", "readiness",
    }
    assert not (fields & forbidden)


# ---------------------------------------------------------------------------
# PedroCore Integration Contract V1
# ---------------------------------------------------------------------------


def test_supported_envelope_version_is_accepted():
    assert is_supported(INTEGRATION_ENVELOPE_V1)
    assert version_status(INTEGRATION_ENVELOPE_V1) is ContractVersionStatus.SUPPORTED


def test_unknown_envelope_version_is_rejected_fail_closed():
    manifest = _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.QUALITY_EVIDENCE,
            contract_versions=(QUALITY_EVIDENCE_V1,),
        )
    )
    envelope = _envelope(_quality_payload(), envelope_version="pedrocore-integration/v7")
    result = _validate(envelope, manifest)
    assert not result.accepted
    assert result.error_code == CONTRACT_VERSION_UNKNOWN


def test_unknown_version_is_never_guessed():
    assert version_status("nao-existe/v1") is ContractVersionStatus.UNKNOWN
    assert not is_supported("nao-existe/v1")
    assert not is_supported("")


def test_envelope_rejects_payload_that_contradicts_declared_type():
    """Adivinhar o tipo pelo formato faria a governanca aceitar o que nao declarou.

    O envelope tenta validar o payload contra o modelo do tipo DECLARADO e
    falha — em vez de reparar que "parece" outro contrato e aceitar assim
    mesmo. A recusa e o comportamento; a mensagem exata do Pydantic nao e
    contrato e por isso nao e afirmada aqui.
    """
    with pytest.raises(ValidationError):
        PedroCoreIntegrationEnvelopeV1.model_validate(
            _envelope(_execution_payload(), payload_type="quality_evidence")
        )

    # O caminho inverso tambem: um payload de qualidade declarado como execucao.
    with pytest.raises(ValidationError):
        PedroCoreIntegrationEnvelopeV1.model_validate(
            _envelope(_quality_payload(), payload_type="execution_outcome")
        )


def test_envelope_requires_a_registered_manifest():
    result = _validate(_envelope(_quality_payload()), None)
    assert not result.accepted
    assert result.error_code == CONTRACT_MANIFEST_MISSING


def test_envelope_rejects_non_object_payload():
    result = _validate("nao sou um envelope", _manifest())
    assert not result.accepted
    assert result.error_code == CONTRACT_PAYLOAD_INVALID


def test_envelope_requires_timezone_aware_submission():
    manifest = _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.QUALITY_EVIDENCE,
            contract_versions=(QUALITY_EVIDENCE_V1,),
        )
    )
    envelope = _envelope(_quality_payload(), submitted_at="2026-08-29T12:00:00")
    result = _validate(envelope, manifest)
    assert not result.accepted
    assert result.error_code == CONTRACT_PAYLOAD_INVALID


def test_envelope_forbids_unknown_top_level_fields():
    manifest = _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.QUALITY_EVIDENCE,
            contract_versions=(QUALITY_EVIDENCE_V1,),
        )
    )
    result = _validate(_envelope(_quality_payload(), surprise="x"), manifest)
    assert not result.accepted
    assert result.error_code == CONTRACT_PAYLOAD_INVALID


def test_validation_errors_never_echo_the_rejected_value():
    """Ecoar o valor devolveria ao log o dado que o contrato acabou de recusar."""
    manifest = _manifest(
        CapabilityDeclaration(
            capability=ProjectCapability.QUALITY_EVIDENCE,
            contract_versions=(QUALITY_EVIDENCE_V1,),
        )
    )
    secreto = "token-super-secreto-do-consumidor"
    result = _validate(_envelope(_quality_payload(evidence_id={"x": secreto})), manifest)
    assert not result.accepted
    assert secreto not in (result.reason or "")


# ---------------------------------------------------------------------------
# Fronteira de autoridade
# ---------------------------------------------------------------------------


def test_reserved_authority_is_detected_at_any_depth():
    """Esconder o campo fundo nao pode ser mais eficaz do que envia-lo no topo."""
    violations = scan_for_reserved_authority(
        {"metadata": {"extra": {"nested": {"eligibility": "eligible"}}}}
    )
    assert [item.path for item in violations] == [
        "$.metadata.extra.nested.eligibility"
    ]


def test_reserved_authority_detects_camel_and_kebab_spellings():
    for spelling in ("trainingCandidate", "training-candidate", "training_candidate"):
        assert scan_for_reserved_authority({spelling: {}}), spelling


def test_producer_assertion_prefix_is_allowed():
    """`producer_asserted_outcome` e alegacao; `eligibility` e sentenca."""
    assert not scan_for_reserved_authority(
        {"producer_asserted_outcome": "successful", "observed_severity": "low"}
    )


def test_reserved_names_cover_the_governance_vocabulary():
    reserved = reserved_field_names()
    for name in ("eligibility", "authorized", "trainingcandidate", "readiness",
                 "qualityscore", "automaticcollection"):
        assert name in reserved


def test_authority_scan_ignores_values_and_only_reads_field_names():
    """O modulo reconhece autoridade indevida; ele nao existe para ler dado."""
    assert not scan_for_reserved_authority({"summary": "eligibility: eligible"})


# ---------------------------------------------------------------------------
# Migracao dos acoplamentos de projeto
# ---------------------------------------------------------------------------


def test_core_modules_no_longer_branch_on_project_names():
    """O nome pode viver no REGISTRO; nunca no MOTOR.

    Se alguem reintroduzir `project_id == "finguard"` na orquestracao ou no
    prompt builder para resolver um caso pontual, este teste falha e a
    conversa acontece antes do merge.
    """
    import ast
    from pathlib import Path

    core_modules = [
        "orchestration/service.py",
        "prompt_builder/service.py",
        "artifact_reader/service.py",
        "exploration/playwright_adapter.py",
    ]
    project_names = {"finguard", "finguard-local", "structa", "elyra", "rivvo", "orlabyte"}
    modules_dir = Path(__file__).resolve().parents[1] / "app" / "modules"

    offenders: list[str] = []
    for relative in core_modules:
        source = (modules_dir / relative).read_text(encoding="utf-8-sig")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                literals = [
                    operand.value
                    for operand in [node.left, *node.comparators]
                    if isinstance(operand, ast.Constant) and isinstance(operand.value, str)
                ]
                if any(item.lower() in project_names for item in literals):
                    offenders.append(f"{relative}:{node.lineno}")
            if isinstance(node, ast.Compare) and any(
                isinstance(op, ast.In) for op in node.ops
            ):
                if (
                    isinstance(node.left, ast.Constant)
                    and isinstance(node.left.value, str)
                    and node.left.value.lower() in project_names
                ):
                    offenders.append(f"{relative}:{node.lineno}")
    assert not offenders, (
        f"Comparacao por nome de projeto no core generico: {offenders}. "
        "Use capability/trait do Project Capability Manifest."
    )


def test_idempotent_submission_is_driven_by_trait_not_by_name():
    assert has_trait("elyra", ProducerTrait.IDEMPOTENT_SUBMISSION)
    assert not has_trait("structa", ProducerTrait.IDEMPOTENT_SUBMISSION)
    assert not has_trait("pedrocore", ProducerTrait.IDEMPOTENT_SUBMISSION)


def test_externally_owned_trait_now_covers_every_external_consumer():
    """Correcao real: a comparacao `== "finguard"` nunca alcancava `finguard-local`."""
    for project_id in ("finguard", "finguard-local", "structa", "elyra"):
        assert has_trait(project_id, ProducerTrait.EXTERNALLY_OWNED), project_id
    assert not has_trait("pedrocore", ProducerTrait.EXTERNALLY_OWNED)


def test_protected_resource_markers_come_from_the_manifests():
    markers = protected_resource_markers()
    assert "finguard" in markers
    assert all(marker == marker.lower().strip() for marker in markers)
