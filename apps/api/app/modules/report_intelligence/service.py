import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.modules.caller_identity.schemas import AuthenticatedCallerContext

from app.modules.report_intelligence.schemas import (
    IntelligenceReportEnvelopeV2,
    IntelligenceReportType,
    ReportMemorySummary,
    ReportSignal,
    TechnicalReportInput,
    payload_model_for,
)

# Report Intelligence Foundation (PEDROCORE-MODEL-FOUNDATION-01).
#
# Extração determinística e conservadora de sinais de relatórios técnicos
# enviados por payload. Regras absolutas:
#   - relatórios NÃO são treinamento;
#   - nenhuma persistência (banco, arquivo, embedding, RAG);
#   - nenhuma leitura de repositório externo;
#   - nenhum provider é chamado;
#   - sinais são explicáveis; o serviço não decide sozinho por produção.

PASSED_STATUSES = {"passed", "pass", "success", "ok"}
FAILED_STATUSES = {"failed", "fail", "error"}

_MAX_LIST_ITEMS = 50
_MAX_TEXT_CHARS = 20_000

_PROVIDER_REAL_USED_PATTERNS = [
    r"provider[_\s]real[_\s]used",
    r"\bprovider real (foi )?usado\b",
    r"\breal provider used\b",
]
_PROVIDER_REAL_BLOCKED_PATTERNS = [
    r"provider[_\s]real[_\s]blocked",
    r"\bprovider real bloqueado\b",
]
_DATABASE_RISK_PATTERNS = [
    r"database[_\s]safety[_\s]risk",
    r"\bbanco real (foi )?(usado|utilizado)\b",
    r"\breal database used\b",
    r"\bbanco errado\b",
    r"\bwrong database\b",
]
_DATABASE_OK_PATTERNS = [
    r"database[_\s]safety[_\s]ok",
    r"\bbanco real n[ãa]o (foi )?(usado|utilizado)\b",
    r"\breal database not used\b",
    r"\bsem banco real\b",
]
_RELEASE_GATE_BLOCKED_PATTERNS = [
    r"release[_\s]gate[_\s]blocked",
    r"\brelease gate bloqueado\b",
]
_RELEASE_GATE_PASSED_PATTERNS = [
    r"release[_\s]gate[_\s]passed",
    r"\brelease gate aprovado\b",
]
_DOCUMENTATION_GAP_PATTERNS = [
    r"documentation[_\s]gap",
    r"\bdocumenta[çc][ãa]o (desatualizada|ausente|incompleta)\b",
]
_HUMAN_REVIEW_PATTERNS = [
    r"review[_\s]required",
    r"human[_\s]review[_\s]required",
    r"can[_\s]advance\s*[=:]\s*false",
    r"\brevis[ãa]o humana\b",
]
_ARCHITECTURE_RISK_PATTERNS = [
    r"qa[_\s]risk[_\s]critical",
    r"architecture[_\s]risk",
]


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned[:_MAX_TEXT_CHARS] if cleaned else None


def _clean_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = (value or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned[:_MAX_TEXT_CHARS])
        if len(result) >= _MAX_LIST_ITEMS:
            break
    return result


def _clean_evidence(values: list[str | dict[str, Any]]) -> list[str | dict[str, Any]]:
    result: list[str | dict[str, Any]] = []
    for value in values[:_MAX_LIST_ITEMS]:
        if isinstance(value, str):
            cleaned = _clean_text(value)
            if cleaned is not None:
                result.append(cleaned)
        elif isinstance(value, dict):
            result.append(dict(value))
    return result


def _matches_any(patterns: list[str], corpus: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, corpus, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


class ReportIntelligenceService:
    def adapt_v1(
        self,
        report: TechnicalReportInput,
        caller: AuthenticatedCallerContext,
    ) -> IntelligenceReportEnvelopeV2:
        """Adapta V1 ao envelope interno V2 sem confiar provenance ao payload."""
        legacy_type = report.report_type.strip().lower()
        try:
            report_type = IntelligenceReportType(legacy_type)
        except ValueError:
            report_type = IntelligenceReportType.QA_EVIDENCE

        common: dict[str, Any] = {
            "status": report.status,
            "legacy_report_type": legacy_type,
            "source": report.source,
            "branch": report.branch,
            "commit": report.commit,
            "summary": report.summary,
            "safety_flags": list(report.safety_flags),
            "findings": list(report.findings),
            "suggested_fixes": list(report.suggested_fixes),
            "next_steps": list(report.next_steps),
            "signals": list(report.signals),
            "evidence": list(report.evidence),
            "metadata": dict(report.metadata or {}),
        }
        payload_type = payload_model_for(report_type)
        return IntelligenceReportEnvelopeV2.model_validate(
            {
                "report_id": report.report_id or str(uuid.uuid4()),
                "report_type": report_type,
                "producer": caller.credential_id,
                "project_id": report.project_id,
                "run_id": report.run_id,
                "conversation_id": report.conversation_id,
                "created_at": report.created_at
                or datetime.now(timezone.utc).isoformat(),
                "payload": payload_type(**common).model_dump(),
            }
        )

    def normalize_envelope(
        self, report: IntelligenceReportEnvelopeV2
    ) -> IntelligenceReportEnvelopeV2:
        payload_data = report.payload.model_dump()
        for field in (
            "status",
            "legacy_report_type",
            "source",
            "branch",
            "commit",
            "summary",
        ):
            if field in payload_data:
                payload_data[field] = _clean_text(payload_data[field])
        payload_data["status"] = (payload_data["status"] or "").lower()
        for field in (
            "safety_flags",
            "findings",
            "suggested_fixes",
            "next_steps",
        ):
            payload_data[field] = _clean_list(payload_data[field])
        payload_data["evidence"] = _clean_evidence(payload_data["evidence"])
        payload_data["signals"] = [dict(item) for item in payload_data["signals"]]
        return IntelligenceReportEnvelopeV2(
            schema_version=report.schema_version,
            report_id=report.report_id.strip(),
            report_type=report.report_type,
            producer=report.producer.strip(),
            project_id=report.project_id.strip().lower(),
            run_id=_clean_text(report.run_id),
            conversation_id=_clean_text(report.conversation_id),
            created_at=report.created_at.strip(),
            payload=type(report.payload)(**payload_data),
        )

    def technical_view(
        self, report: IntelligenceReportEnvelopeV2
    ) -> TechnicalReportInput:
        normalized = self.normalize_envelope(report)
        payload = normalized.payload
        return TechnicalReportInput(
            report_id=normalized.report_id,
            project_id=normalized.project_id,
            report_type=payload.legacy_report_type or normalized.report_type.value,
            source=payload.source,
            run_id=normalized.run_id,
            conversation_id=normalized.conversation_id,
            branch=payload.branch,
            commit=payload.commit,
            status=payload.status,
            summary=payload.summary,
            safety_flags=payload.safety_flags,
            findings=payload.findings,
            suggested_fixes=payload.suggested_fixes,
            next_steps=payload.next_steps,
            signals=payload.signals,
            evidence=payload.evidence,
            created_at=normalized.created_at,
            metadata=payload.metadata,
        )

    def normalize_report(self, report: TechnicalReportInput) -> TechnicalReportInput:
        """Normalização determinística: trim, lowercase de status, dedupe de listas."""
        return TechnicalReportInput(
            project_id=report.project_id.strip().lower(),
            report_type=report.report_type.strip().lower(),
            report_id=_clean_text(report.report_id),
            source=_clean_text(report.source),
            run_id=_clean_text(report.run_id),
            conversation_id=_clean_text(report.conversation_id),
            branch=_clean_text(report.branch),
            commit=_clean_text(report.commit),
            status=report.status.strip().lower(),
            summary=_clean_text(report.summary),
            safety_flags=_clean_list(report.safety_flags),
            findings=_clean_list(report.findings),
            suggested_fixes=_clean_list(report.suggested_fixes),
            next_steps=_clean_list(report.next_steps),
            signals=[dict(item) for item in report.signals],
            evidence=_clean_evidence(report.evidence),
            created_at=_clean_text(report.created_at),
            metadata=dict(report.metadata or {}),
        )

    def extract_signals_v2(
        self, report: IntelligenceReportEnvelopeV2
    ) -> list[ReportSignal]:
        return self.extract_signals(self.technical_view(report))

    def extract_signals(self, report: TechnicalReportInput) -> list[ReportSignal]:
        """Extrai sinais conservadores e explicáveis; nunca decide sozinho."""
        normalized = self.normalize_report(report)
        corpus_parts = [
            normalized.status,
            normalized.summary or "",
            *normalized.safety_flags,
            *normalized.findings,
        ]
        corpus = "\n".join(corpus_parts)

        signals: list[ReportSignal] = []

        def add(
            signal_type: str,
            severity: str,
            summary: str,
            evidence: str | None,
            confidence: float,
        ) -> None:
            signals.append(
                ReportSignal(
                    project_id=normalized.project_id,
                    report_type=normalized.report_type,
                    signal_type=signal_type,
                    severity=severity,
                    summary=summary,
                    evidence=evidence,
                    confidence=confidence,
                    source_run_id=normalized.run_id,
                    source_commit=normalized.commit,
                    created_at=normalized.created_at,
                )
            )

        status_passed = normalized.status in PASSED_STATUSES
        status_failed = normalized.status in FAILED_STATUSES

        if status_passed:
            severity = "low" if normalized.findings else "info"
            add(
                "qa_passed",
                severity,
                "Relatório indica execução com sucesso.",
                f"status={normalized.status}",
                0.9,
            )
        elif status_failed:
            add(
                "qa_failed",
                "high",
                "Relatório indica falha na execução.",
                f"status={normalized.status}",
                0.9,
            )

        evidence = _matches_any(_PROVIDER_REAL_USED_PATTERNS, corpus)
        if evidence:
            add(
                "provider_real_used",
                "critical",
                "Relatório indica uso de provider real; exige revisão humana.",
                evidence,
                0.8,
            )
        evidence = _matches_any(_PROVIDER_REAL_BLOCKED_PATTERNS, corpus)
        if evidence:
            add(
                "provider_real_blocked",
                "info",
                "Provider real foi bloqueado pelo safe mode (comportamento esperado).",
                evidence,
                0.8,
            )

        # Negação primeiro: "banco real não usado" contém "banco real".
        ok_evidence = _matches_any(_DATABASE_OK_PATTERNS, corpus)
        if ok_evidence:
            add(
                "database_safety_ok",
                "info",
                "Relatório indica que nenhum banco real foi usado.",
                ok_evidence,
                0.8,
            )
        else:
            risk_evidence = _matches_any(_DATABASE_RISK_PATTERNS, corpus)
            if risk_evidence:
                add(
                    "database_safety_risk",
                    "critical",
                    "Relatório indica possível uso de banco real; exige revisão humana.",
                    risk_evidence,
                    0.8,
                )

        if re.search(r"\bsmoke\b", corpus, re.IGNORECASE):
            add(
                "smoke_coverage",
                "medium",
                "Cobertura reportada é smoke (parcial); não tratar como cobertura completa.",
                "smoke",
                0.7,
            )
        if re.search(r"\bfull\b", corpus, re.IGNORECASE):
            add(
                "full_coverage",
                "info",
                "Relatório menciona cobertura full.",
                "full",
                0.7,
            )

        evidence = _matches_any(_DOCUMENTATION_GAP_PATTERNS, corpus)
        if evidence:
            add(
                "documentation_gap",
                "low",
                "Relatório indica lacuna de documentação.",
                evidence,
                0.7,
            )

        evidence = _matches_any(_RELEASE_GATE_BLOCKED_PATTERNS, corpus)
        if evidence:
            add(
                "release_gate_blocked",
                "high",
                "Release gate bloqueado segundo o relatório.",
                evidence,
                0.8,
            )
        evidence = _matches_any(_RELEASE_GATE_PASSED_PATTERNS, corpus)
        if evidence:
            add(
                "release_gate_passed",
                "info",
                "Release gate aprovado segundo o relatório.",
                evidence,
                0.8,
            )

        evidence = _matches_any(_HUMAN_REVIEW_PATTERNS, corpus)
        if evidence:
            add(
                "human_review_required",
                "high" if status_failed else "medium",
                "Relatório exige revisão humana antes de avançar.",
                evidence,
                0.8,
            )

        evidence = _matches_any(_ARCHITECTURE_RISK_PATTERNS, corpus)
        if evidence:
            # QA_RISK_CRITICAL vira sinal de risco de arquitetura, mas não
            # invalida automaticamente uma suíte reportada como passed.
            add(
                "architecture_risk",
                "critical",
                "Risco crítico de arquitetura/QA sinalizado; revisão humana obrigatória.",
                evidence,
                0.7,
            )

        for step in normalized.next_steps:
            add(
                "next_step",
                "info",
                f"Próximo passo recomendado: {step}",
                None,
                0.9,
            )

        return signals

    def summarize_memory(
        self,
        project_id: str,
        reports: list[TechnicalReportInput],
    ) -> ReportMemorySummary:
        """Agrega sinais em memória técnica em memória volátil — sem persistência."""
        normalized_project = project_id.strip().lower()
        project_reports = [
            self.normalize_report(report)
            for report in reports
            if report.project_id.strip().lower() == normalized_project
        ]

        if not project_reports:
            return ReportMemorySummary(project_id=normalized_project)

        last_report = project_reports[-1]

        important: list[ReportSignal] = []
        unresolved_risks: list[str] = []
        milestones: list[str] = []
        next_steps: list[str] = []

        for report in project_reports:
            for signal in self.extract_signals(report):
                if signal.severity in {"medium", "high", "critical"}:
                    important.append(signal)
                if signal.signal_type in {"qa_failed", "database_safety_risk",
                                          "architecture_risk", "release_gate_blocked"}:
                    unresolved_risks.append(signal.summary)
                if signal.signal_type in {"qa_passed", "release_gate_passed"}:
                    milestones.append(signal.summary)
            for step in report.next_steps:
                if step not in next_steps:
                    next_steps.append(step)

        return ReportMemorySummary(
            project_id=normalized_project,
            last_known_status=last_report.status,
            important_signals=important,
            unresolved_risks=list(dict.fromkeys(unresolved_risks)),
            completed_milestones=list(dict.fromkeys(milestones)),
            next_recommended_steps=next_steps,
            updated_at=last_report.created_at,
        )


report_intelligence_service = ReportIntelligenceService()
