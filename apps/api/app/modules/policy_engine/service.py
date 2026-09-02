"""Servico do Policy Engine. Fail-closed por construcao."""

from __future__ import annotations

import hashlib

from app.modules.policy_engine.rules import (
    POLICY_REQUIREMENTS_SATISFIED,
    rules_for,
)
from app.modules.policy_engine.schemas import (
    PolicyDecision,
    PolicyEffect,
    PolicyEvaluation,
    PolicyRequest,
    PolicyRuleMatch,
    decision_for,
)


class PolicyEngineService:
    """Avalia uma requisicao contra as regras transversais declaradas.

    Duas propriedades sustentam o resto:

    Determinismo — os mesmos atributos produzem a mesma decisao. Nao ha
    relogio, nao ha aleatoriedade, nao ha provider. Por isso `policy_id` pode
    ser derivado do proprio conteudo da requisicao, e duas avaliacoes iguais
    sao rastreavelmente a mesma avaliacao.

    Fail-closed — decisao so pode ser afrouxada por regra que casou; erro,
    ausencia de atributo e efeito desconhecido caem para o lado restritivo.
    """

    def evaluate(self, request: PolicyRequest) -> PolicyEvaluation:
        matches: list[PolicyRuleMatch] = []
        for rule in rules_for(request.domain):
            try:
                match = rule.evaluate(request)
            except Exception:  # noqa: BLE001
                # Regra que explode nao pode virar permissao. Ela vira revisao
                # humana, com o proprio id no motivo para ser consertada.
                matches.append(
                    PolicyRuleMatch(
                        rule_id=rule.rule_id,
                        rule_version=rule.version,
                        domain=rule.domain,
                        effect=PolicyEffect.REVIEW,
                        reason_code="POLICY_RULE_EVALUATION_FAILED",
                        explanation=(
                            "Regra de política falhou ao avaliar; a decisão foi "
                            "encaminhada para revisão humana em vez de liberada."
                        ),
                    )
                )
                continue
            if match is not None:
                matches.append(match)

        decision = decision_for([item.effect for item in matches])
        conditions = [
            rule.condition
            for rule in rules_for(request.domain)
            if rule.condition
            and any(item.rule_id == rule.rule_id for item in matches)
        ]
        reason_codes = sorted({item.reason_code for item in matches}) or [
            POLICY_REQUIREMENTS_SATISFIED
        ]

        return PolicyEvaluation(
            policy_id=self._policy_id(request),
            decision=decision,
            domain=request.domain,
            action=request.action,
            project_id=request.project_id.strip().lower(),
            reason_codes=reason_codes,
            matched_rules=matches,
            conditions=conditions,
            correlation_id=request.correlation_id,
        )

    @staticmethod
    def _policy_id(request: PolicyRequest) -> str:
        """Identificador derivado do conteudo avaliado.

        Deriva-lo em vez de sortea-lo torna a avaliacao reproduzivel: repetir
        a mesma pergunta devolve o mesmo `policy_id`, e duas linhas de auditoria
        com o mesmo id sao comprovadamente a mesma pergunta.
        """
        payload = "|".join(
            [
                request.domain.value,
                request.action.strip().lower(),
                request.project_id.strip().lower(),
                request.environment.strip().lower(),
                request.producer.strip().lower(),
                ";".join(
                    f"{key}={request.attributes[key]}"
                    for key in sorted(request.attributes)
                ),
            ]
        )
        return "policy_" + hashlib.sha256(payload.encode()).hexdigest()[:24]

    def allows(self, request: PolicyRequest) -> bool:
        """Atalho de leitura. DENY e REVIEW_REQUIRED nao liberam."""
        return self.evaluate(request).allowed


policy_engine_service = PolicyEngineService()

__all__ = [
    "PolicyDecision",
    "PolicyEngineService",
    "PolicyEvaluation",
    "PolicyRequest",
    "policy_engine_service",
]
