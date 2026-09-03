from __future__ import annotations

import hashlib

from app.modules.artifacts.schemas import ArtifactProcessingResult
from app.modules.caller_identity.schemas import AuthenticatedCallerContext
from app.modules.operational_memory.schemas import (
    EvidenceEffect,
    EvidenceReferenceInput,
    EvidenceSourceType,
    LearningCandidateInput,
    PatternType,
)
from app.modules.operational_memory.service import operational_memory_service
from app.modules.qa_analysis.service import qa_text_analyzer
from app.modules.qa_response.service import qa_response_service
from app.modules.report_intelligence.schemas import (
    ExecutionOutcomePayload,
    IntelligenceReportEnvelopeV2,
    IntelligenceReportType,
)
from app.modules.report_intelligence.service import report_intelligence_service
from app.modules.report_memory.service import report_memory_service
from app.modules.risk_engine.execution_contract_schemas import (
    ContractValidationRequest,
    RiskGate,
)
from app.modules.risk_engine.execution_contract_service import execution_contract_service
from app.modules.risk_engine.persistence_service import risk_persistence_service
from app.modules.risk_engine.repository import RiskRepositoryError
from app.modules.risk_engine.scope import canonical_scopes
from app.modules.risk_engine.post_execution_schemas import (
    ExecutionComparison,
    ExecutionEvidence,
    OperationalMemoryProjection,
    PostExecutionOutcome,
    PredictedVsActual,
)


def _outcome_id(evidence_id: str, contract_id: str) -> str:
    digest = hashlib.sha256(f"{evidence_id}:{contract_id}".encode()).hexdigest()[:24]
    return f"outcome_{digest}"


class PostExecutionService:
    @staticmethod
    def _effective_gate(evidence: ExecutionEvidence) -> RiskGate:
        contract_gate = evidence.contract.gate
        review = evidence.human_review
        if review is None:
            return contract_gate
        if review.contract_id != evidence.contract.contract_id:
            return RiskGate.BLOCK
        if not execution_contract_service.review_integrity_valid(review):
            return RiskGate.BLOCK
        return review.resulting_gate

    @staticmethod
    def _qa(evidence: ExecutionEvidence):
        lines: list[str] = []
        for item in evidence.tests:
            lines.append(
                f"{item.suite}: {item.passed} passed, {item.failed} failed, "
                f"{item.skipped} skipped; status {item.status}."
            )
        if not lines:
            lines.append("No tests reported.")
        artifact = ArtifactProcessingResult(
            count=1,
            types=["structured_execution_evidence"],
            names=[evidence.evidence_id],
            text_block="\n".join(lines),
            analysis_text="\n".join(lines),
            textual_count=1,
        )
        analysis = qa_text_analyzer.analyze("release_gate_review", artifact)
        skeleton = qa_response_service.build_skeleton(
            "release_gate_review",
            fallback_used=False,
            artifacts_result=artifact,
            analysis=analysis,
            safe_mode_blocked=False,
        )
        assert skeleton is not None
        release_gate = qa_response_service.evaluate_release_gate(
            artifact,
            analysis,
            fallback_used=False,
            safe_mode_blocked=False,
            provider_used="local_qa",
        )
        return skeleton, release_gate

    @staticmethod
    def _compare(evidence: ExecutionEvidence) -> ExecutionComparison:
        contract = evidence.contract
        # `file:` aqui ja era canonicalizacao — feita a mao, so para arquivo,
        # e so deste lado. Agora os dois lados passam pela mesma funcao.
        actual_files = sorted({f"file:{item}" for item in evidence.files_changed})
        actual_targets = sorted(set(actual_files) | set(canonical_scopes(evidence.scope_changes)))
        allowed_scope = set(canonical_scopes(contract.allowed_scope))
        unexpected_files = sorted(set(actual_files) - set(canonical_scopes(contract.allowed_files)))
        scope_deviation = sorted(set(actual_targets) - allowed_scope)
        allowed_commands = set(contract.allowed_commands)
        forbidden_commands = sorted(
            item.command_id for item in evidence.commands if item.command not in allowed_commands
        )
        failed_tests = sorted(
            item.suite for item in evidence.tests if item.status == "failed" or item.failed > 0
        )
        security_findings = sorted(
            item.scanner
            for item in evidence.security_results
            if item.status == "failed" or item.critical > 0 or item.high > 0
        )
        migration_incidents = sorted(
            item.migration_id
            for item in evidence.migration_results
            if item.status in {"failed", "rolled_back"}
        )
        reasons: list[str] = []
        if unexpected_files:
            reasons.append("UNEXPECTED_FILES")
        if scope_deviation:
            reasons.append("SCOPE_DEVIATION")
        if forbidden_commands:
            reasons.append("FORBIDDEN_OPERATIONS")
        if failed_tests:
            reasons.append("FAILED_TESTS")
        if security_findings:
            reasons.append("SECURITY_FINDINGS")
        if migration_incidents:
            reasons.append("MIGRATION_INCIDENTS")
        if evidence.unexpected_effects:
            reasons.append("UNEXPECTED_EFFECTS")
        if evidence.files_changed and evidence.diff is None:
            reasons.append("DIFF_EVIDENCE_MISSING")
        return ExecutionComparison(
            intent_targets=sorted(set(evidence.current_request.requested_operation.targets)),
            actual_targets=actual_targets,
            unexpected_files=unexpected_files,
            scope_deviation=scope_deviation,
            forbidden_commands=forbidden_commands,
            failed_tests=failed_tests,
            security_findings=security_findings,
            migration_incidents=migration_incidents,
            unexpected_effects=sorted(set(evidence.unexpected_effects)),
            reason_codes=reasons,
        )

    def process(
        self,
        evidence: ExecutionEvidence,
        caller: AuthenticatedCallerContext,
    ) -> PostExecutionOutcome:
        validation = execution_contract_service.validate(
            ContractValidationRequest(
                producer=evidence.producer,
                contract=evidence.contract,
                current_request=evidence.current_request,
            )
        )
        effective_gate = self._effective_gate(evidence)
        comparison = self._compare(evidence)
        qa, qa_release_gate = self._qa(evidence)
        contract_usable = (
            validation.integrity_valid
            and validation.context_valid
            and not validation.expired
            and effective_gate in {RiskGate.PASS, RiskGate.PASS_WITH_WARNINGS}
        )
        reason_codes = list(comparison.reason_codes)
        if not contract_usable:
            reason_codes.append("EXECUTION_CONTRACT_NOT_USABLE")
        if not qa_release_gate.can_advance:
            reason_codes.append("QA_GATE_BLOCKED")
        reason_codes = sorted(set(reason_codes))
        status = "passed" if not reason_codes else "failed" if contract_usable else "blocked"
        predicted = dict(evidence.contract.risk_dimensions)
        predicted_active = {key for key, value in predicted.items() if value >= 0.4}
        actual_dimension = {
            "SCOPE_DEVIATION": "scope_risk",
            "UNEXPECTED_FILES": "scope_risk",
            "FAILED_TESTS": "regression_risk",
            "SECURITY_FINDINGS": "security_risk",
            "MIGRATION_INCIDENTS": "migration_risk",
            "FORBIDDEN_OPERATIONS": "operational_risk",
            "UNEXPECTED_EFFECTS": "operational_risk",
        }
        actual_active = {
            actual_dimension[code] for code in reason_codes if code in actual_dimension
        }
        predicted_vs_actual = PredictedVsActual(
            predicted_dimensions=predicted,
            actual_issue_codes=reason_codes,
            predicted_risk_materialized=bool(predicted_active & actual_active),
            unpredicted_issue_detected=bool(actual_active - predicted_active),
        )
        outcome_id = _outcome_id(evidence.evidence_id, evidence.contract.contract_id)
        report = report_intelligence_service.normalize_envelope(
            IntelligenceReportEnvelopeV2(
                report_id=outcome_id,
                report_type=IntelligenceReportType.EXECUTION_OUTCOME,
                producer=caller.credential_id,
                project_id=evidence.project_id.strip().lower(),
                run_id=evidence.evidence_id,
                payload=ExecutionOutcomePayload(
                    status=status,
                    summary="Comparação pós-execução estruturada concluída.",
                    findings=reason_codes,
                    safety_flags=([] if status == "passed" else ["review_required"]),
                    signals=[
                        {
                            "signal_type": "qa_passed" if status == "passed" else "qa_failed",
                            "source": "post-execution-v1",
                        }
                    ],
                    evidence=[
                        {"evidence_id": evidence.evidence_id},
                        {"contract_id": evidence.contract.contract_id},
                    ],
                    metadata={
                        "risk_analysis_id": evidence.contract.analysis_id,
                        "risk_policy_version": evidence.contract.risk_policy_version,
                        "contract_gate": evidence.contract.gate.value,
                        "effective_gate": effective_gate.value,
                        "predicted_dimensions": predicted,
                        "actual_issue_codes": reason_codes,
                    },
                    outcome=status,
                    scope_deviation=bool(comparison.scope_deviation),
                    qa_passed=qa_release_gate.can_advance,
                ),
            )
        )
        entry, _snapshot, _signals, _evaluation, _warnings, duplicate = (
            report_memory_service.ingest_envelope(report)
        )
        memory_projection = OperationalMemoryProjection()
        if entry is not None:
            is_success = status == "passed"
            primary = reason_codes[0].lower() if reason_codes else "contract_compliance"
            candidate, memory, candidate_duplicate, _candidate_warnings = (
                operational_memory_service.ingest_candidate(
                    LearningCandidateInput(
                        candidate_id=f"candidate-{outcome_id}",
                        producer=caller.credential_id,
                        project_id=evidence.project_id,
                        pattern_type=(
                            PatternType.SUCCESS_PATTERN if is_success else PatternType.RISK_PATTERN
                        ),
                        pattern_key=f"execution.{primary}",
                        task_type="post_execution_verification",
                        summary=(
                            "Execution matched signed contract and QA evidence."
                            if is_success
                            else "Execution produced a bounded post-execution risk signal."
                        ),
                        evidence=[
                            EvidenceReferenceInput(
                                source_type=EvidenceSourceType.REPORT,
                                source_id=report.report_id,
                                effect=EvidenceEffect.SUPPORTS,
                            )
                        ],
                    ),
                    caller,
                )
            )
            memory_projection = OperationalMemoryProjection(
                candidate_id=candidate.candidate_id if candidate else None,
                memory_id=memory.memory_id if memory else None,
                lifecycle=memory.lifecycle.value if memory else None,
                duplicate=candidate_duplicate,
            )
        outcome = PostExecutionOutcome(
            outcome_id=outcome_id,
            project_id=evidence.project_id.strip().lower(),
            evidence_id=evidence.evidence_id,
            contract_id=evidence.contract.contract_id,
            risk_analysis_id=evidence.contract.analysis_id,
            effective_gate=effective_gate,
            status=status,
            contract_valid=contract_usable,
            comparison=comparison,
            predicted_vs_actual=predicted_vs_actual,
            qa=qa,
            qa_release_gate=qa_release_gate,
            execution_outcome_report=report,
            report_persisted=entry is not None,
            report_duplicate=duplicate,
            operational_memory=memory_projection,
            trace=[
                evidence.current_request.request_id,
                evidence.contract.analysis_id,
                evidence.contract.contract_id,
                evidence.evidence_id,
                outcome_id,
                report.report_id,
            ],
        )
        # Stage R2: o observado tambem vira historia propria do dominio Risk,
        # ao lado — nao no lugar — de Report Memory e Operational Memory.
        try:
            risk_persistence_service.record_outcome(outcome)
        except RiskRepositoryError:
            pass
        return outcome


post_execution_service = PostExecutionService()
