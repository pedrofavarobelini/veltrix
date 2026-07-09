import asyncio
import uuid
from datetime import datetime, timezone

from app.modules.chat.schemas import ChatRequest
from app.modules.eval_harness.fixtures import DEFAULT_EVAL_CASES
from app.modules.eval_harness.schemas import EvalCase, EvalCaseResult, EvalRunResult
from app.modules.orchestration.service import orchestration_service

# Eval Harness determinístico (PEDROCORE-EVAL-HARNESS-01).
#
# Mede segurança, coerência e regressões de resposta rodando casos fixos
# contra o pipeline real com providers seguros. NÃO é benchmark de LLM:
# não chama provider real, não chama internet, não depende de modelo local.


class EvalHarnessService:
    async def run(self, cases: list[EvalCase] | None = None) -> EvalRunResult:
        selected = cases if cases is not None else DEFAULT_EVAL_CASES
        results: list[EvalCaseResult] = []

        for case in selected:
            results.append(await self._run_case(case))

        passed = sum(1 for result in results if result.passed)
        failed = len(results) - passed

        return EvalRunResult(
            run_id=str(uuid.uuid4()),
            total=len(results),
            passed=passed,
            failed=failed,
            risk_level="none" if failed == 0 else "high",
            cases=results,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def run_sync(self, cases: list[EvalCase] | None = None) -> EvalRunResult:
        return asyncio.run(self.run(cases))

    async def _run_case(self, case: EvalCase) -> EvalCaseResult:
        payload = ChatRequest(
            message=case.input,
            mode=case.mode,
            provider=case.provider,
            task_type=case.task_type,
            origin_system=case.project_id,
            context=case.context,
            artifacts=case.artifacts,
            allow_real_provider=False,
            allow_local_model=case.allow_local_model,
            context_from_memory=case.context_from_memory,
        )
        outcome = await orchestration_service.execute(payload)

        failures: list[str] = []
        answer_lower = outcome.answer.lower()

        for requirement in case.expected_requirements:
            if requirement.lower() not in answer_lower:
                failures.append(f"requisito ausente na resposta: '{requirement}'")

        for pattern in case.forbidden_patterns:
            if pattern.lower() in answer_lower:
                failures.append(f"padrão proibido presente na resposta: '{pattern}'")

        outcome_codes = set(outcome.warning_codes)
        for code in case.expected_warnings:
            if code not in outcome_codes:
                failures.append(f"warning esperado ausente: '{code}'")

        plan_flags = (
            set(outcome.intelligence_plan.safety_flags)
            if outcome.intelligence_plan is not None
            else set()
        )
        for flag in case.expected_safety_flags:
            if flag not in plan_flags:
                failures.append(f"safety flag esperada ausente: '{flag}'")

        if case.expect_release_can_advance is not None:
            if outcome.release_gate is None:
                failures.append("release_gate esperado, mas ausente")
            elif outcome.release_gate.can_advance != case.expect_release_can_advance:
                failures.append(
                    "release_gate.can_advance="
                    f"{outcome.release_gate.can_advance}, esperado "
                    f"{case.expect_release_can_advance}"
                )

        if case.expect_memory_used is not None:
            if outcome.memory_used != case.expect_memory_used:
                failures.append(
                    f"memory_used={outcome.memory_used}, esperado "
                    f"{case.expect_memory_used}"
                )

        return EvalCaseResult(
            case_id=case.case_id,
            passed=not failures,
            failures=failures,
            provider_used=outcome.provider_used,
            task_type=outcome.task_type,
        )


eval_harness_service = EvalHarnessService()
