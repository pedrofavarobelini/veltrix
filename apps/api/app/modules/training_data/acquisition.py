from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone

from app.modules.caller_identity.schemas import (
    AuthenticatedCallerContext,
    CallerRole,
    IdentityStrength,
)
from app.modules.report_memory.repository import ReportMemoryRepositoryConfigurationError
from app.modules.report_memory.service import (
    FLAG_DATABASE_URL,
    MODE_MEMORY,
    MODE_POSTGRESQL,
    persistence_mode,
)
from app.modules.training_data.adapters import training_source_adapters
from app.modules.training_data.policy import training_eligibility_policy
from app.modules.training_data.repository import (
    InMemoryTrainingCandidateRepository,
    PostgreSQLTrainingCandidateRepository,
    TrainingCandidateRepository,
)
from app.modules.training_data.schemas import (
    CandidateLifecycle,
    DataUseAuthorization,
    DatasetReadinessMetrics,
    DatasetReadinessPolicy,
    DatasetReadinessReport,
    EligibilityDecision,
    FingerprintDistribution,
    PrivacyClassification,
    TrainingAuthorizationRequest,
    TrainingCandidateProposal,
    TrainingCandidateRecord,
    TrainingCandidateReviewRequest,
    TrainingCandidateStatusRequest,
    TrainingExampleCandidateDraft,
    TrainingPurpose,
    TrainingSourceSelection,
    TrainingSourceType,
)
from app.modules.training_data.service import dataset_foundation_service

FLAG_TRAINING_DATA_ADMIN_IDS = "PEDROCORE_TRAINING_DATA_ADMIN_IDS"
FLAG_READINESS_MIN_AUTHORIZED = "PEDROCORE_DATASET_READINESS_MIN_AUTHORIZED"


class TrainingCandidateTransitionError(RuntimeError):
    def __init__(self, code: str, reason_codes: list[str] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.reason_codes = reason_codes or [code]


def _hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _fingerprint(proposal: TrainingCandidateProposal) -> str:
    stable = proposal.model_dump(mode="json", exclude={"proposed_at"})
    for evidence in stable["evidence_refs"]:
        evidence.pop("observed_at", None)
    return _hash(stable)


def _candidate_id(
    selection: TrainingSourceSelection,
    fingerprint: str,
) -> str:
    stable = {
        "project_id": selection.project_id.strip().lower(),
        "source_type": selection.source_type.value,
        "source_id": selection.source_id.strip(),
        "training_purpose": selection.training_purpose.value,
        "fingerprint": fingerprint,
    }
    return "training-candidate-" + _hash(stable).split(":", 1)[1][:24]


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def readiness_policy_from_environment() -> DatasetReadinessPolicy:
    raw = (os.environ.get(FLAG_READINESS_MIN_AUTHORIZED) or "").strip()
    if not raw:
        return DatasetReadinessPolicy()
    try:
        minimum = int(raw)
    except ValueError:
        return DatasetReadinessPolicy()
    if minimum < 1:
        return DatasetReadinessPolicy()
    return DatasetReadinessPolicy(minimum_authorized_candidates=minimum)


class TrainingCandidateAcquisitionService:
    """Opt-in operacional; nunca varre fontes, cria dataset ou inicia treinamento."""

    automatic_collection = False

    def __init__(self) -> None:
        self._memory_repository = InMemoryTrainingCandidateRepository()
        self._postgres_repositories: dict[str, PostgreSQLTrainingCandidateRepository] = {}

    @staticmethod
    def admin_authorized(caller: AuthenticatedCallerContext) -> bool:
        allowed = {
            item.strip()
            for item in (os.environ.get(FLAG_TRAINING_DATA_ADMIN_IDS) or "").split(",")
            if item.strip()
        }
        return (
            caller.identity_strength is IdentityStrength.REGISTERED
            and caller.caller_role is CallerRole.TECHNICAL_TOOL
            and caller.credential_id in allowed
        )

    def _repository(self) -> TrainingCandidateRepository | None:
        mode = persistence_mode()
        if mode == MODE_MEMORY:
            return self._memory_repository
        if mode == MODE_POSTGRESQL:
            database_url = (os.environ.get(FLAG_DATABASE_URL) or "").strip()
            if not database_url:
                raise ReportMemoryRepositoryConfigurationError(
                    f"{FLAG_DATABASE_URL} é obrigatória no modo postgresql."
                )
            repository = self._postgres_repositories.get(database_url)
            if repository is None:
                repository = PostgreSQLTrainingCandidateRepository(database_url)
                self._postgres_repositories[database_url] = repository
            return repository
        if mode == "local_json":
            raise ReportMemoryRepositoryConfigurationError(
                "Candidate Store não suporta local_json; use memory ou postgresql."
            )
        return None

    def reset(self) -> None:
        self._memory_repository.clear()
        self._postgres_repositories.clear()

    def select(
        self,
        selection: TrainingSourceSelection,
        caller: AuthenticatedCallerContext,
    ) -> tuple[TrainingCandidateRecord, bool]:
        repository = self._required_repository()
        trusted_selection = selection.model_copy(
            update={
                "producer": caller.credential_id,
                "project_id": selection.project_id.strip().lower(),
                "source_id": selection.source_id.strip(),
            }
        )
        proposal = training_source_adapters.select(trusted_selection)
        pre_screen = training_eligibility_policy.pre_screen(proposal)
        fingerprint = _fingerprint(proposal)
        candidate_id = _candidate_id(trusted_selection, fingerprint)
        now = datetime.now(timezone.utc)

        if pre_screen.decision is EligibilityDecision.ELIGIBLE:
            lifecycle = CandidateLifecycle.PROPOSED
            eligibility = EligibilityDecision.NOT_ELIGIBLE
            reason_codes = ["TRAINING_AUTHORIZATION_REQUIRED"]
        elif pre_screen.decision is EligibilityDecision.REQUIRES_REVIEW:
            lifecycle = CandidateLifecycle.REVIEW_REQUIRED
            eligibility = EligibilityDecision.REQUIRES_REVIEW
            reason_codes = pre_screen.reason_codes
        else:
            lifecycle = CandidateLifecycle.EXCLUDED
            eligibility = EligibilityDecision.NOT_ELIGIBLE
            reason_codes = pre_screen.reason_codes

        privacy_rejected = (
            pre_screen.privacy_classification is PrivacyClassification.REJECTED_SENSITIVE
        )
        record = TrainingCandidateRecord(
            candidate_id=candidate_id,
            project_id=trusted_selection.project_id,
            source_type=trusted_selection.source_type,
            source_id=None if privacy_rejected else trusted_selection.source_id,
            source_reference_hash=_hash(
                {
                    "project_id": trusted_selection.project_id,
                    "source_type": trusted_selection.source_type.value,
                    "source_id": trusted_selection.source_id,
                }
            ),
            fingerprint=fingerprint,
            task_type="privacy-rejected" if privacy_rejected else proposal.task_type,
            training_purpose=trusted_selection.training_purpose,
            lifecycle=lifecycle,
            eligibility=eligibility,
            privacy_classification=pre_screen.privacy_classification,
            reason_codes=reason_codes,
            privacy_findings=pre_screen.privacy_findings,
            proposal=None if privacy_rejected else proposal,
            created_at=now,
            updated_at=now,
        )
        if repository.add(record):
            return record, False
        existing = repository.get(record.project_id, record.candidate_id)
        if existing is None:
            raise ReportMemoryRepositoryConfigurationError(
                "Candidate Store recusou idempotência sem registro existente."
            )
        return existing, True

    def authorize(
        self,
        candidate_id: str,
        request: TrainingAuthorizationRequest,
        caller: AuthenticatedCallerContext,
    ) -> TrainingCandidateRecord:
        repository = self._required_repository()
        record = self._required_record(repository, request.project_id, candidate_id)
        if record.lifecycle is not CandidateLifecycle.PROPOSED or record.proposal is None:
            raise TrainingCandidateTransitionError("CANDIDATE_NOT_AUTHORIZABLE")

        purpose = record.training_purpose
        evaluation_only = purpose is TrainingPurpose.EVALUATION_ONLY
        if evaluation_only != (request.basis == "evaluation_only"):
            raise TrainingCandidateTransitionError("AUTHORIZATION_BASIS_PURPOSE_MISMATCH")
        if request.authorized_scope.strip().lower() != record.task_type.strip().lower():
            raise TrainingCandidateTransitionError("AUTHORIZED_SCOPE_MISMATCH")
        now = datetime.now(timezone.utc)
        authorization = DataUseAuthorization(
            authorized=True,
            allows_neural_training=not evaluation_only,
            basis=request.basis,
            authorized_by=caller.credential_id,
            authorized_at=now,
            authorized_project=record.project_id,
            authorized_scope=request.authorized_scope,
            training_purpose=purpose,
            authorization_source=request.authorization_source,
            content_classification=request.content_classification,
            confidential_content_approved=request.confidential_content_approved,
        )
        eligibility = training_eligibility_policy.evaluate(
            record.proposal,
            authorization,
            review_approved=record.review_approved,
        )
        if eligibility.decision is not EligibilityDecision.ELIGIBLE:
            raise TrainingCandidateTransitionError(
                "CANDIDATE_NOT_ELIGIBLE",
                eligibility.reason_codes,
            )

        draft = TrainingExampleCandidateDraft(
            producer=record.proposal.producer,
            source_type=record.proposal.source_type,
            project_id=record.proposal.project_id,
            task_type=record.proposal.task_type,
            input_features=record.proposal.input_features,
            context_features=record.proposal.context_features,
            target=record.proposal.target,
            evidence_refs=record.proposal.evidence_refs,
            quality_signals=record.proposal.quality_signals,
            feedback=record.proposal.feedback,
            risk_metadata=record.proposal.risk_metadata,
            data_use=authorization,
            derived_content_only=True,
            created_at=record.proposal.proposed_at,
        )
        foundation = dataset_foundation_service.evaluate(draft)
        if foundation.status != "eligible" or foundation.candidate is None:
            raise TrainingCandidateTransitionError(
                "DATASET_FOUNDATION_REJECTED",
                foundation.rejection_codes,
            )
        candidate = foundation.candidate.model_copy(update={"candidate_id": record.candidate_id})
        updated = record.model_copy(
            update={
                "lifecycle": CandidateLifecycle.AUTHORIZED,
                "eligibility": EligibilityDecision.ELIGIBLE,
                "reason_codes": [],
                "authorization": authorization,
                "candidate": candidate,
                "updated_at": now,
            }
        )
        self._replace(repository, updated, {CandidateLifecycle.PROPOSED})
        return updated

    def review(
        self,
        candidate_id: str,
        request: TrainingCandidateReviewRequest,
        caller: AuthenticatedCallerContext,
    ) -> TrainingCandidateRecord:
        repository = self._required_repository()
        record = self._required_record(repository, request.project_id, candidate_id)
        if record.lifecycle is not CandidateLifecycle.REVIEW_REQUIRED:
            raise TrainingCandidateTransitionError("CANDIDATE_NOT_REVIEWABLE")
        now = datetime.now(timezone.utc)
        if request.decision == "exclude":
            updated = record.model_copy(
                update={
                    "lifecycle": CandidateLifecycle.EXCLUDED,
                    "eligibility": EligibilityDecision.NOT_ELIGIBLE,
                    "excluded_reason": request.reason_code,
                    "reviewed_by": caller.credential_id,
                    "reviewed_at": now,
                    "updated_at": now,
                }
            )
        else:
            updated = record.model_copy(
                update={
                    "lifecycle": CandidateLifecycle.PROPOSED,
                    "eligibility": EligibilityDecision.NOT_ELIGIBLE,
                    "reason_codes": ["TRAINING_AUTHORIZATION_REQUIRED"],
                    "review_approved": True,
                    "reviewed_by": caller.credential_id,
                    "reviewed_at": now,
                    "updated_at": now,
                }
            )
        self._replace(repository, updated, {CandidateLifecycle.REVIEW_REQUIRED})
        return updated

    def exclude(
        self,
        candidate_id: str,
        request: TrainingCandidateStatusRequest,
        caller: AuthenticatedCallerContext,
    ) -> TrainingCandidateRecord:
        repository = self._required_repository()
        record = self._required_record(repository, request.project_id, candidate_id)
        allowed = {
            CandidateLifecycle.PROPOSED,
            CandidateLifecycle.REVIEW_REQUIRED,
            CandidateLifecycle.AUTHORIZED,
        }
        if record.lifecycle not in allowed:
            raise TrainingCandidateTransitionError("CANDIDATE_NOT_EXCLUDABLE")
        updated = record.model_copy(
            update={
                "lifecycle": CandidateLifecycle.EXCLUDED,
                "eligibility": EligibilityDecision.NOT_ELIGIBLE,
                "excluded_reason": request.reason_code,
                "reviewed_by": caller.credential_id,
                "reviewed_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._replace(repository, updated, allowed)
        return updated

    def revoke(
        self,
        candidate_id: str,
        request: TrainingCandidateStatusRequest,
        caller: AuthenticatedCallerContext,
    ) -> TrainingCandidateRecord:
        repository = self._required_repository()
        record = self._required_record(repository, request.project_id, candidate_id)
        allowed = {CandidateLifecycle.AUTHORIZED, CandidateLifecycle.CONSUMED}
        if record.lifecycle not in allowed:
            raise TrainingCandidateTransitionError("CANDIDATE_NOT_REVOCABLE")
        now = datetime.now(timezone.utc)
        updated = record.model_copy(
            update={
                "lifecycle": CandidateLifecycle.REVOKED,
                "eligibility": EligibilityDecision.NOT_ELIGIBLE,
                "revoked_reason": request.reason_code,
                "revoked_by": caller.credential_id,
                "revoked_at": now,
                "updated_at": now,
            }
        )
        self._replace(repository, updated, allowed)
        return updated

    def mark_consumed(
        self,
        project_id: str,
        candidate_id: str,
        dataset_id: str,
    ) -> TrainingCandidateRecord:
        """Integração futura da Etapa 13; deliberadamente não exposta por API nesta etapa."""
        repository = self._required_repository()
        record = self._required_record(repository, project_id, candidate_id)
        if record.lifecycle is not CandidateLifecycle.AUTHORIZED:
            raise TrainingCandidateTransitionError("CANDIDATE_NOT_CONSUMABLE")
        lineage = list(record.consumed_dataset_ids)
        if dataset_id not in lineage:
            lineage.append(dataset_id)
        updated = record.model_copy(
            update={
                "lifecycle": CandidateLifecycle.CONSUMED,
                "consumed_dataset_ids": lineage,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._replace(repository, updated, {CandidateLifecycle.AUTHORIZED})
        return updated

    def page(
        self,
        project_id: str,
        *,
        lifecycle: CandidateLifecycle | None,
        source_type: TrainingSourceType | None,
        training_purpose: TrainingPurpose | None,
        task_type: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[TrainingCandidateRecord], int]:
        repository = self._required_repository()
        normalized_project = project_id.strip().lower()
        return (
            repository.list(
                normalized_project,
                lifecycle=lifecycle,
                source_type=source_type,
                training_purpose=training_purpose,
                task_type=task_type,
                limit=limit,
                offset=offset,
            ),
            repository.count(
                normalized_project,
                lifecycle=lifecycle,
                source_type=source_type,
                training_purpose=training_purpose,
                task_type=task_type,
            ),
        )

    def readiness(
        self,
        project_id: str,
        policy: DatasetReadinessPolicy | None = None,
    ) -> DatasetReadinessReport:
        repository = self._required_repository()
        normalized_project = project_id.strip().lower()
        records = repository.list(normalized_project)
        active = [
            item
            for item in records
            if item.lifecycle in {CandidateLifecycle.AUTHORIZED, CandidateLifecycle.CONSUMED}
            and item.eligibility is EligibilityDecision.ELIGIBLE
        ]
        fingerprints = Counter(item.fingerprint for item in records)
        duplicate_items = sum(count - 1 for count in fingerprints.values() if count > 1)
        metrics = DatasetReadinessMetrics(
            total_candidates=len(records),
            authorized_candidates=len(active),
            eligible_candidates=len(active),
            review_required=sum(
                item.lifecycle is CandidateLifecycle.REVIEW_REQUIRED for item in records
            ),
            excluded=sum(item.lifecycle is CandidateLifecycle.EXCLUDED for item in records),
            revoked=sum(item.lifecycle is CandidateLifecycle.REVOKED for item in records),
            by_source=dict(Counter(item.source_type.value for item in records)),
            by_project={normalized_project: len(records)} if records else {},
            by_task_type=dict(Counter(item.task_type for item in records)),
            by_training_purpose=dict(
                Counter(item.training_purpose.value for item in records)
            ),
            with_known_outcome=sum(
                bool(item.proposal and item.proposal.quality_signals.outcome_known)
                for item in active
            ),
            with_qa_evidence=sum(
                bool(item.proposal and item.proposal.quality_signals.qa_validated)
                for item in active
            ),
            with_human_feedback=sum(
                bool(item.proposal and item.proposal.quality_signals.human_feedback_present)
                for item in active
            ),
            with_verified_provenance=sum(
                bool(item.proposal and all(ref.verified for ref in item.proposal.evidence_refs))
                for item in active
            ),
            contradictions=sum(
                bool(item.proposal and item.proposal.quality_signals.contradiction_detected)
                for item in active
            ),
            privacy_rejections=sum(
                item.privacy_classification is PrivacyClassification.REJECTED_SENSITIVE
                for item in records
            ),
            fingerprint_distribution=FingerprintDistribution(
                unique_fingerprints=len(fingerprints),
                duplicate_groups=sum(count > 1 for count in fingerprints.values()),
                max_frequency=max(fingerprints.values(), default=0),
                duplicate_ratio=_ratio(duplicate_items, len(records)),
            ),
        )
        readiness_policy = policy or readiness_policy_from_environment()
        blockers = self._readiness_blockers(metrics, active, readiness_policy)
        return DatasetReadinessReport(
            project_id=normalized_project,
            readiness="DATASET_NOT_READY" if blockers else "DATASET_READY",
            policy=readiness_policy,
            metrics=metrics,
            blocker_codes=blockers,
        )

    @staticmethod
    def _readiness_blockers(
        metrics: DatasetReadinessMetrics,
        active: list[TrainingCandidateRecord],
        policy: DatasetReadinessPolicy,
    ) -> list[str]:
        blockers: set[str] = set()
        total = len(active)
        if policy.minimum_authorized_candidates is None:
            blockers.add("READINESS_VOLUME_POLICY_NOT_CONFIGURED")
        elif total < policy.minimum_authorized_candidates:
            blockers.add("INSUFFICIENT_AUTHORIZED_VOLUME")
        if len({item.source_type for item in active}) < policy.minimum_source_types:
            blockers.add("INSUFFICIENT_SOURCE_DIVERSITY")
        if len({item.task_type for item in active}) < policy.minimum_task_types:
            blockers.add("INSUFFICIENT_TASK_DIVERSITY")
        if len({item.training_purpose for item in active}) < policy.minimum_training_purposes:
            blockers.add("INSUFFICIENT_PURPOSE_COVERAGE")
        if _ratio(metrics.with_known_outcome, total) < policy.minimum_known_outcome_ratio:
            blockers.add("INSUFFICIENT_KNOWN_OUTCOMES")
        if _ratio(metrics.with_qa_evidence, total) < policy.minimum_qa_coverage_ratio:
            blockers.add("INSUFFICIENT_QA_COVERAGE")
        if (
            _ratio(metrics.with_verified_provenance, total)
            < policy.minimum_verified_provenance_ratio
        ):
            blockers.add("INSUFFICIENT_VERIFIED_PROVENANCE")
        if (
            metrics.fingerprint_distribution.duplicate_ratio
            > policy.maximum_duplicate_ratio
        ):
            blockers.add("DUPLICATION_RATIO_EXCEEDED")
        if _ratio(metrics.contradictions, total) > policy.maximum_contradiction_ratio:
            blockers.add("CONTRADICTION_RATIO_EXCEEDED")
        return sorted(blockers)

    def _required_repository(self) -> TrainingCandidateRepository:
        repository = self._repository()
        if repository is None:
            raise ReportMemoryRepositoryConfigurationError(
                "Candidate Store desabilitado; nenhum fallback foi aplicado."
            )
        return repository

    @staticmethod
    def _required_record(
        repository: TrainingCandidateRepository,
        project_id: str,
        candidate_id: str,
    ) -> TrainingCandidateRecord:
        record = repository.get(project_id.strip().lower(), candidate_id.strip())
        if record is None:
            raise TrainingCandidateTransitionError("CANDIDATE_NOT_FOUND")
        return record

    @staticmethod
    def _replace(
        repository: TrainingCandidateRepository,
        updated: TrainingCandidateRecord,
        expected: set[CandidateLifecycle],
    ) -> None:
        if not repository.replace(updated, expected_lifecycles=expected):
            raise TrainingCandidateTransitionError("CANDIDATE_CONCURRENT_TRANSITION")


training_candidate_service = TrainingCandidateAcquisitionService()
