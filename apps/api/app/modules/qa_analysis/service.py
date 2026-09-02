import re

from app.modules.artifacts.schemas import ArtifactProcessingResult
from app.modules.contracts import codes
from app.modules.qa_analysis.schemas import QATextAnalysisResult
from app.modules.task_router.service import CRITICAL_TASK_TYPES

# Analisador textual local e determinístico.
# Nunca lê arquivos, nunca executa comandos, nunca chama provider real,
# nunca depende de rede ou de chave externa.

SUCCESS_PATTERNS = [
    r"\ball tests passed\b",
    r"\btests passed\b",
    r"\b\d+ passed\b",
    r"\bpassed\b",
    r"\bpass\b",
    r"\bsuccess\b",
    r"\bbuild successful\b",
    r"\b0 failed\b",
    r"100%",
    r"\bok\b",
]

FAILURE_PATTERNS = [
    r"\bfailed tests\b",
    r"\btest failed\b",
    r"\bbuild failed\b",
    r"\blint failed\b",
    r"\bruff failed\b",
    r"\beslint failed\b",
    r"\bmypy failed\b",
    r"\btypecheck failed\b",
    r"\btsc failed\b",
    r"\bcoverage failed\b",
    r"\bfailed\b",
    r"\bfailures?\b",
    r"\bfailing\b",
    r"\bassertionerror\b",
    r"\berro no teste\b",
    r"\bteste falhou\b",
]

ERROR_PATTERNS = [
    r"\b500 internal server error\b",
    r"\bstack trace\b",
    r"\btraceback\b",
    r"\bsyntaxerror\b",
    r"\btypeerror\b",
    r"\bvalueerror\b",
    r"\bimporterror\b",
    r"\bmodule not found\b",
    r"\bcannot import\b",
    r"\bexceptions?\b",
    r"\berrors?\b",
    r"\bcrash(es|ed)?\b",
    r"\berros?\b",
    r"exce[çc][ãa]o",
]

WARNING_PATTERNS = [
    r"\bdeprecationwarnings?\b",
    r"\bdeprecated\b",
    r"\bwarnings?\b",
    r"\bwarn\b",
    r"\bavisos?\b",
]

CRITICAL_PATTERNS = [
    r"\bprodu[çc][ãa]o\b",
    r"\bproduction\b",
    r"\bprod\b",
    r"\bbanco real\b",
    r"\bdatabase real\b",
    r"\breal database\b",
    r"\blive database\b",
    r"\bwrong database\b",
    r"\bbanco errado\b",
    r"\bmigration destrutiva\b",
    r"\bdestructive migration\b",
    r"\bdrop table\b",
    r"\btruncate\b",
    r"\bdelete from\b",
    r"\bapagar dados\b",
    r"\bresetar banco\b",
    r"\bsecrets?\b",
    r"\btokens?\b",
    r"\bpasswords?\b",
    r"\bsenhas?\b",
    r"\bapi key\b",
    r"\bapikey\b",
    r"\bprivate key\b",
    r"\bcredentials\b",
    r"\.env\b",
    r"\bprovider real\b",
    r"\bdeploy\b",
    r"\brelease em produ[çc][ãa]o\b",
]

QA_ANALYSIS_NO_ARTIFACTS_WARNING = (
    "Sem artefatos textuais suficientes para análise QA."
)

QA_ANALYSIS_NO_EVIDENCE_WARNING = (
    "Sem evidência textual conclusiva para análise QA."
)

QA_LOCAL_HEURISTIC_WARNING = (
    "Análise QA textual local e determinística (heurística); "
    "não substitui validação humana e não houve execução de testes pelo Veltrix."
)

SAFE_COMMANDS_BASE = [
    "git status --short",
    "python -m pytest",
]

SAFE_COMMANDS_FAILURE = [
    "python -m pytest",
    "Reexecutar apenas o teste que falhou, se identificado no relatório.",
    "Revisar logs locais completos antes de avançar.",
    "git status --short",
]

SAFE_COMMANDS_CRITICAL = [
    "Pausar o fluxo e validar o relatório de QA manualmente.",
    "Conferir configuração de banco de teste antes de qualquer execução.",
    "Verificar se o ambiente de teste está isolado de produção.",
    "git status --short",
]

SAFE_FIXES_FAILURE = [
    "Investigar a causa da falha antes de aplicar correção.",
    "Corrigir testes quebrados antes de avançar.",
    "Revisar o traceback para identificar o ponto de falha.",
]

SAFE_FIXES_CRITICAL = [
    "Separar evidência de ambiente local de qualquer referência a produção.",
    "Remover segredos/tokens do artefato antes de reenviar.",
    "Revisar configuração de ambiente se houver indício de banco incorreto.",
]

SAFE_FIXES_WARNING = [
    "Tratar warnings relevantes antes de release gate.",
]


def _find_matches(patterns: list[str], text: str) -> list[str]:
    found: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            found.add(match.group(0))
    return sorted(found)


class QATextAnalyzer:
    def analyze(
        self,
        task_type: str,
        artifacts_result: ArtifactProcessingResult,
        fallback_used: bool = False,
        safe_mode_blocked: bool = False,
    ) -> QATextAnalysisResult | None:
        if task_type not in CRITICAL_TASK_TYPES:
            return None

        risk_floor = "high" if artifacts_result.path_rejected else "medium"

        if artifacts_result.count == 0 or artifacts_result.textual_count == 0:
            return QATextAnalysisResult(
                analyzed=False,
                status="not_analyzed",
                summary="Sem artefatos textuais processáveis; análise QA não realizada.",
                risk_level=risk_floor,
                can_advance=False,
                confidence=0.0,
                warnings=[QA_ANALYSIS_NO_ARTIFACTS_WARNING],
                warning_codes=[codes.QA_NO_ARTIFACTS],
                suggested_commands=list(SAFE_COMMANDS_BASE),
            )

        text = artifacts_result.analysis_text.lower()
        # "0 failed" é evidência de sucesso; mascarar antes da detecção de falha.
        text_for_failures = re.sub(r"\b0 failed\b", "zero-falhas", text)

        successes = _find_matches(SUCCESS_PATTERNS, text)
        failures = _find_matches(FAILURE_PATTERNS, text_for_failures)
        errors = _find_matches(ERROR_PATTERNS, text_for_failures)
        warns = _find_matches(WARNING_PATTERNS, text)
        critical_hits = _find_matches(CRITICAL_PATTERNS, text)

        if not (successes or failures or errors or warns or critical_hits):
            return QATextAnalysisResult(
                analyzed=False,
                status="not_analyzed",
                summary="Artefatos recebidos, mas sem evidência textual conclusiva.",
                risk_level=risk_floor,
                can_advance=False,
                confidence=0.0,
                warnings=[QA_ANALYSIS_NO_EVIDENCE_WARNING],
                warning_codes=[codes.QA_NO_ARTIFACTS],
                suggested_commands=list(SAFE_COMMANDS_BASE),
            )

        has_blockers = bool(failures or errors)

        if critical_hits:
            risk_level = "critical"
        elif has_blockers or artifacts_result.path_rejected:
            risk_level = "high"
        elif warns and not successes:
            risk_level = "medium"
        elif successes:
            risk_level = "low"
        else:
            risk_level = "medium"

        if has_blockers:
            status = "fail"
        elif critical_hits:
            status = "warning"
        elif successes and warns:
            status = "warning"
        elif successes:
            status = "pass"
        else:
            status = "warning"

        if not (successes or failures or errors):
            confidence = 0.4
        elif has_blockers or critical_hits:
            confidence = 0.85
        elif successes and warns:
            confidence = 0.7
        else:
            confidence = 0.9

        can_advance = (
            status == "pass"
            and risk_level == "low"
            and not has_blockers
            and not critical_hits
            and bool(successes)
            and not fallback_used
            and not safe_mode_blocked
            and not artifacts_result.path_rejected
            and not artifacts_result.truncated
        )

        probable_causes: list[str] = []
        if failures:
            probable_causes.append("Falhas de teste detectadas no artefato textual.")
        if errors:
            probable_causes.append("Erros/exceções detectados no artefato textual.")
        if critical_hits:
            probable_causes.append(
                "Indício de ambiente/dados sensíveis (produção, banco real ou segredo) no relatório."
            )
        if warns and not (failures or errors):
            probable_causes.append("Warnings presentes no relatório.")

        if critical_hits:
            suggested_commands = list(SAFE_COMMANDS_CRITICAL)
            suggested_fixes = list(SAFE_FIXES_CRITICAL)
        elif has_blockers:
            suggested_commands = list(SAFE_COMMANDS_FAILURE)
            suggested_fixes = list(SAFE_FIXES_FAILURE)
        elif warns:
            suggested_commands = list(SAFE_COMMANDS_BASE)
            suggested_fixes = list(SAFE_FIXES_WARNING)
        else:
            suggested_commands = list(SAFE_COMMANDS_BASE)
            suggested_fixes = []

        warning_texts = [QA_LOCAL_HEURISTIC_WARNING]
        warning_codes_list = [codes.QA_LOCAL_HEURISTIC]
        if failures:
            warning_codes_list.append(codes.QA_FAILURE_DETECTED)
            warning_texts.append("Falha detectada em artefato textual de QA.")
        if errors:
            warning_codes_list.append(codes.QA_ERROR_DETECTED)
            warning_texts.append("Erro/exceção detectado em artefato textual de QA.")
        if warns:
            warning_codes_list.append(codes.QA_WARNING_DETECTED)
            warning_texts.append("Warnings detectados em artefato textual de QA.")
        if critical_hits:
            warning_codes_list.append(codes.QA_RISK_CRITICAL)
            warning_texts.append(
                "Risco crítico detectado em artefato textual de QA (produção/segredo/dado real)."
            )

        summary = (
            f"Análise textual local: {len(successes)} sinal(is) de sucesso, "
            f"{len(failures)} de falha, {len(errors)} de erro, "
            f"{len(warns)} aviso(s), {len(critical_hits)} sinal(is) crítico(s); "
            f"risco {risk_level}."
        )

        return QATextAnalysisResult(
            analyzed=True,
            status=status,
            summary=summary,
            detected_successes=successes,
            detected_failures=failures,
            detected_errors=errors,
            detected_warnings=warns,
            detected_critical=critical_hits,
            findings=successes + warns,
            failures=failures + errors,
            probable_causes=probable_causes,
            suggested_commands=suggested_commands,
            suggested_fixes=suggested_fixes,
            risk_level=risk_level,
            can_advance=can_advance,
            confidence=confidence,
            warnings=warning_texts,
            warning_codes=warning_codes_list,
        )


qa_text_analyzer = QATextAnalyzer()
