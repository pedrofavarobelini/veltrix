import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.modules.contracts import codes
from app.modules.contracts.codes import WarningItem, make_warning
from app.modules.evaluation.schemas import EvaluationResult
from app.modules.evaluation.service import evaluation_service
from app.modules.report_intelligence.schemas import (
    IntelligenceReportEnvelopeV2,
    ReportSignal,
    TechnicalReportInput,
)
from app.modules.report_intelligence.service import report_intelligence_service
from app.modules.report_memory.repository import (
    InMemoryReportMemoryRepository,
    LocalJsonReportMemoryRepository,
)
from app.modules.report_memory.schemas import ProjectMemorySnapshot, ReportMemoryEntry

# Memória técnica controlada (PEDROCORE-REPORT-MEMORY-01).
#
# Regras absolutas:
#   - relatórios NÃO treinam IA, NÃO fazem fine-tuning e NÃO alteram
#     comportamento automaticamente; viram sinais/histórico consultável;
#   - default OFF (PEDROCORE_REPORT_MEMORY_PERSISTENCE=off): nada é guardado;
#   - "memory" guarda in-process (volátil); "local_json" persiste apenas no
#     diretório configurado pelo operador;
#   - conteúdo é sanitizado (segredos redigidos) antes de guardar;
#   - nenhuma leitura de arquivo/repositório externo.

FLAG_PERSISTENCE = "PEDROCORE_REPORT_MEMORY_PERSISTENCE"
FLAG_MEMORY_DIR = "PEDROCORE_REPORT_MEMORY_DIR"

MODE_OFF = "off"
MODE_MEMORY = "memory"
MODE_LOCAL_JSON = "local_json"
VALID_MODES = {MODE_OFF, MODE_MEMORY, MODE_LOCAL_JSON}

MEMORY_DISABLED_WARNING = (
    "Memória técnica desabilitada (PEDROCORE_REPORT_MEMORY_PERSISTENCE=off); "
    "nada foi guardado nem consultado."
)
MEMORY_EMPTY_WARNING = "Memória técnica sem registros para este projeto."
MEMORY_USED_WARNING = (
    "Snapshot de memória técnica anexado ao contexto (limitado e sanitizado); "
    "memória técnica não é treinamento."
)

MAX_CONTEXT_BLOCK_CHARS = 2_000
_SNAPSHOT_LIST_LIMIT = 5

_SECRET_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|senha|chave)\b\s*[:=]\s*\S+"
)


def persistence_mode() -> str:
    raw = (os.environ.get(FLAG_PERSISTENCE) or MODE_OFF).strip().lower()
    return raw if raw in VALID_MODES else MODE_OFF


def _redact(text: str | None) -> str | None:
    if text is None:
        return None
    return _SECRET_PATTERN.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)


def _redact_list(values: list[str]) -> list[str]:
    return [redacted for value in values if (redacted := _redact(value)) is not None]


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return _redact(value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if re.search(r"(?i)(api[_-]?key|secret|token|password|senha|chave)", key):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = _sanitize_value(item)
        return sanitized
    return value


class ReportMemoryService:
    def __init__(self) -> None:
        self._memory_repo = InMemoryReportMemoryRepository()
        self._json_repos: dict[str, LocalJsonReportMemoryRepository] = {}

    # -- infra -----------------------------------------------------------

    def enabled(self) -> bool:
        return persistence_mode() != MODE_OFF

    def _repository(self) -> InMemoryReportMemoryRepository | None:
        mode = persistence_mode()
        if mode == MODE_MEMORY:
            return self._memory_repo
        if mode == MODE_LOCAL_JSON:
            directory = (os.environ.get(FLAG_MEMORY_DIR) or "").strip()
            if not directory:
                return None
            repo = self._json_repos.get(directory)
            if repo is None:
                repo = LocalJsonReportMemoryRepository(directory)
                self._json_repos[directory] = repo
            return repo
        return None

    def reset(self) -> None:
        """Limpa o estado in-process (uso em testes)."""
        self._memory_repo.clear()
        self._json_repos.clear()

    # -- análise sem persistência -----------------------------------------

    def analyze(
        self, report: TechnicalReportInput
    ) -> tuple[TechnicalReportInput, list[ReportSignal], EvaluationResult]:
        normalized = report_intelligence_service.normalize_report(report)
        signals = report_intelligence_service.extract_signals(normalized)
        evaluation = evaluation_service.evaluate_report_signals(signals)
        return normalized, signals, evaluation

    def analyze_envelope(
        self, report: IntelligenceReportEnvelopeV2
    ) -> tuple[IntelligenceReportEnvelopeV2, list[ReportSignal], EvaluationResult]:
        normalized = report_intelligence_service.normalize_envelope(report)
        signals = report_intelligence_service.extract_signals_v2(normalized)
        evaluation = evaluation_service.evaluate_report_signals(signals)
        return normalized, signals, evaluation

    # -- ingestão ---------------------------------------------------------

    def ingest(
        self, report: TechnicalReportInput
    ) -> tuple[
        ReportMemoryEntry | None,
        ProjectMemorySnapshot | None,
        list[ReportSignal],
        EvaluationResult,
        list[WarningItem],
    ]:
        normalized, signals, evaluation = self.analyze(report)
        entry, snapshot, warnings, _duplicate = self._persist(
            normalized,
            signals,
            report_id=normalized.report_id,
            schema_version="1",
            producer=None,
            conversation_id=normalized.conversation_id,
        )
        return entry, snapshot, signals, evaluation, warnings

    def ingest_envelope(
        self, report: IntelligenceReportEnvelopeV2
    ) -> tuple[
        ReportMemoryEntry | None,
        ProjectMemorySnapshot | None,
        list[ReportSignal],
        EvaluationResult,
        list[WarningItem],
        bool,
    ]:
        normalized, signals, evaluation = self.analyze_envelope(report)
        technical = report_intelligence_service.technical_view(normalized)
        entry, snapshot, warnings, duplicate = self._persist(
            technical,
            signals,
            report_id=normalized.report_id,
            schema_version=normalized.schema_version,
            producer=normalized.producer,
            conversation_id=normalized.conversation_id,
        )
        return entry, snapshot, signals, evaluation, warnings, duplicate

    def _persist(
        self,
        normalized: TechnicalReportInput,
        signals: list[ReportSignal],
        *,
        report_id: str | None,
        schema_version: str,
        producer: str | None,
        conversation_id: str | None,
    ) -> tuple[
        ReportMemoryEntry | None,
        ProjectMemorySnapshot | None,
        list[WarningItem],
        bool,
    ]:
        warnings: list[WarningItem] = [
            make_warning(
                codes.REPORT_MEMORY_IS_NOT_TRAINING,
                "Relatórios não treinam IA; alimentam apenas sinais e memória técnica.",
            )
        ]

        repo = self._repository()
        if repo is None:
            warnings.append(
                make_warning(codes.REPORT_MEMORY_DISABLED, MEMORY_DISABLED_WARNING)
            )
            return None, None, warnings, False

        if report_id is not None:
            existing = repo.get_by_report_id(normalized.project_id, report_id)
            if existing is not None:
                warnings.append(
                    make_warning(
                        codes.REPORT_DUPLICATE_IGNORED,
                        "report_id já ingerido neste projeto; nenhum efeito duplicado foi criado.",
                    )
                )
                return existing, self.snapshot(normalized.project_id), warnings, True

        now = datetime.now(timezone.utc).isoformat()
        entry = ReportMemoryEntry(
            memory_id=str(uuid.uuid4()),
            report_id=report_id,
            schema_version=schema_version,
            producer=producer,
            project_id=normalized.project_id,
            report_type=normalized.report_type,
            source_run_id=normalized.run_id,
            conversation_id=conversation_id,
            source_commit=normalized.commit,
            branch=normalized.branch,
            status=normalized.status,
            summary=_redact(normalized.summary),
            signals=signals,
            safety_flags=_redact_list(normalized.safety_flags),
            unresolved_risks=[
                s.summary
                for s in signals
                if s.signal_type
                in {"qa_failed", "database_safety_risk", "architecture_risk",
                    "release_gate_blocked"}
            ],
            completed_milestones=[
                s.summary
                for s in signals
                if s.signal_type in {"qa_passed", "release_gate_passed"}
            ],
            next_steps=_redact_list(normalized.next_steps),
            findings=_redact_list(normalized.findings),
            suggested_fixes=_redact_list(normalized.suggested_fixes),
            source_signals=_sanitize_value(normalized.signals),
            evidence=_sanitize_value(normalized.evidence),
            created_at=normalized.created_at or now,
            updated_at=now,
            metadata=_sanitize_value(normalized.metadata or {}),
        )
        repo.add(entry)

        return entry, self.snapshot(normalized.project_id), warnings, False

    # -- consulta ---------------------------------------------------------

    def snapshot(self, project_id: str) -> ProjectMemorySnapshot | None:
        repo = self._repository()
        if repo is None:
            return None

        normalized_project = project_id.strip().lower()
        entries = repo.list(normalized_project)
        if not entries:
            return None

        last = entries[-1]
        milestones: list[str] = []
        risks: list[str] = []
        next_steps: list[str] = []
        signal_counts: dict[str, int] = {}

        for entry in entries:
            for item in entry.completed_milestones:
                if item not in milestones:
                    milestones.append(item)
            for item in entry.unresolved_risks:
                if item not in risks:
                    risks.append(item)
            for item in entry.next_steps:
                if item not in next_steps:
                    next_steps.append(item)
            for signal in entry.signals:
                signal_counts[signal.signal_type] = (
                    signal_counts.get(signal.signal_type, 0) + 1
                )

        recurring = sorted(
            [name for name, count in signal_counts.items() if count >= 2]
        )
        confidence = round(min(0.9, 0.3 + 0.1 * len(entries)), 2)

        return ProjectMemorySnapshot(
            project_id=normalized_project,
            last_known_status=last.status,
            last_report_at=last.created_at,
            latest_commit=last.source_commit,
            latest_branch=last.branch,
            completed_milestones=milestones[-_SNAPSHOT_LIST_LIMIT:],
            unresolved_risks=risks[-_SNAPSHOT_LIST_LIMIT:],
            recurring_signals=recurring,
            next_recommended_steps=next_steps[-_SNAPSHOT_LIST_LIMIT:],
            confidence=confidence,
            source_count=len(entries),
        )

    def context_block(self, project_id: str) -> tuple[str | None, list[WarningItem]]:
        """Bloco textual limitado do snapshot para o Prompt Builder.

        Retorna (None, warnings) quando a memória está desabilitada ou vazia.
        """
        if not self.enabled():
            return None, [
                make_warning(codes.REPORT_MEMORY_DISABLED, MEMORY_DISABLED_WARNING)
            ]

        snapshot = self.snapshot(project_id)
        if snapshot is None:
            return None, [
                make_warning(codes.REPORT_MEMORY_EMPTY, MEMORY_EMPTY_WARNING)
            ]

        lines = [
            f"project_id: {snapshot.project_id}",
            f"last_known_status: {snapshot.last_known_status}",
            f"last_report_at: {snapshot.last_report_at}",
            f"source_count: {snapshot.source_count}",
            f"confidence: {snapshot.confidence}",
        ]
        if snapshot.unresolved_risks:
            lines.append("riscos_nao_resolvidos: " + "; ".join(snapshot.unresolved_risks))
        if snapshot.completed_milestones:
            lines.append("marcos_concluidos: " + "; ".join(snapshot.completed_milestones))
        if snapshot.next_recommended_steps:
            lines.append(
                "proximos_passos: " + "; ".join(snapshot.next_recommended_steps)
            )
        lines.append("Nota: memória técnica não é treinamento; é contexto consultável.")

        block = "\n".join(lines)[:MAX_CONTEXT_BLOCK_CHARS]
        return block, [make_warning(codes.REPORT_MEMORY_USED, MEMORY_USED_WARNING)]


report_memory_service = ReportMemoryService()
