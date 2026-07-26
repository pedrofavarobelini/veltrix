"""Matriz de autorização de provider (MULTI-PROVIDER-SAFE-EVOLUTION, Etapa 2).

    project_id + caller_role + environment + provider → permitido ou negado

O default é NEGAR. Autorização não é consequência de existir adapter, existir
chave, estar configurado ou estar registrado: cada combinação precisa estar
explicitamente registrada aqui E o provider precisa estar implementado,
configurado e homologado no catálogo (Etapa 1).

Esta matriz não escolhe provider e não reordena candidatos: ela apenas
autoriza ou nega o provider que o pipeline já selecionaria. `provider=auto`
continua Gemini-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.modules.caller_identity.schemas import CallerRole
from app.modules.contracts import codes
from app.modules.provider_authorization.schemas import (
    AuthorizationResult,
    ProviderAuthorizationDecision,
)
from app.modules.provider_catalog.service import provider_catalog_service

# Ambientes não-produtivos reconhecidos pelo repositório.
NON_PRODUCTION_ENVIRONMENTS = frozenset(
    {"development", "dev", "local", "test", "testing", "qa", "staging"}
)
PRODUCTION_ENVIRONMENTS = frozenset({"prod", "production"})

DENIED_UNREGISTERED_REASON = (
    "Combinação projeto/papel/ambiente/provider não registrada na matriz de "
    "autorização; provider real negado (fail-closed)."
)
DENIED_NOT_IMPLEMENTED_REASON = (
    "Provider sem adapter implementado não pode ser autorizado."
)
DENIED_NOT_CONFIGURED_REASON = (
    "Provider não configurado no ambiente; execução real negada."
)
DENIED_NOT_HOMOLOGATED_REASON = (
    "Provider não homologado; execução real negada até homologação explícita."
)
DENIED_UNKNOWN_PROVIDER_REASON = (
    "Provider fora do catálogo do PedroCore; execução real negada."
)
ALLOWED_REASON = "Combinação registrada na matriz de autorização de providers."
NOT_APPLICABLE_REASON = (
    "Provider não externo: matriz de provider real não se aplica."
)


@dataclass(frozen=True)
class AuthorizationRule:
    """Entrada explícita da matriz. Tudo que não está aqui é negado."""

    project_ids: frozenset[str]
    caller_roles: frozenset[CallerRole]
    environments: frozenset[str]
    providers: frozenset[str]
    notes: str = field(default="")

    def matches(
        self, project_id: str, caller_role: CallerRole, environment: str, provider_id: str
    ) -> bool:
        return (
            project_id in self.project_ids
            and caller_role in self.caller_roles
            and environment in self.environments
            and provider_id in self.providers
        )


# Matriz explícita. Somente Gemini é homologado; nenhum outro provider real é
# autorizado para qualquer projeto, papel ou ambiente nesta frente.
_RULES: tuple[AuthorizationRule, ...] = (
    AuthorizationRule(
        project_ids=frozenset({"finguard", "finguard-local"}),
        caller_roles=frozenset({CallerRole.COMMON_CONSUMER, CallerRole.TECHNICAL_TOOL}),
        environments=NON_PRODUCTION_ENVIRONMENTS | PRODUCTION_ENVIRONMENTS,
        providers=frozenset({"gemini"}),
        notes=(
            "FinGuard consome o PedroCore com provider=auto; Gemini é o único "
            "provider real registrado para o projeto."
        ),
    ),
    AuthorizationRule(
        project_ids=frozenset({"pedrocore"}),
        caller_roles=frozenset({CallerRole.TECHNICAL_TOOL}),
        environments=NON_PRODUCTION_ENVIRONMENTS,
        providers=frozenset({"gemini"}),
        notes=(
            "Uso técnico local do próprio PedroCore; produção não registrada "
            "de propósito."
        ),
    ),
)


class ProviderAuthorizationService:
    """Autorização cumulativa e fail-closed de provider real por projeto."""

    def evaluate(
        self,
        *,
        project_id: str,
        caller_role: CallerRole,
        environment: str,
        provider_id: str,
    ) -> ProviderAuthorizationDecision:
        normalized_project = (project_id or "").strip().lower()
        normalized_environment = (environment or "").strip().lower()
        normalized_provider = (provider_id or "").strip().lower()

        def decide(
            result: AuthorizationResult, reason: str, error_code: str | None = None
        ) -> ProviderAuthorizationDecision:
            return ProviderAuthorizationDecision(
                result=result,
                provider_id=normalized_provider,
                project_id=normalized_project,
                caller_role=caller_role.value,
                environment=normalized_environment,
                error_code=error_code,
                reason=reason,
            )

        definition = provider_catalog_service.get(normalized_provider)
        if definition is None:
            return decide(
                AuthorizationResult.DENIED,
                DENIED_UNKNOWN_PROVIDER_REASON,
                codes.PROVIDER_NOT_AUTHORIZED_FOR_PROJECT,
            )

        if not definition.is_real_provider:
            return decide(AuthorizationResult.NOT_APPLICABLE, NOT_APPLICABLE_REASON)

        if not definition.implemented:
            return decide(
                AuthorizationResult.DENIED,
                DENIED_NOT_IMPLEMENTED_REASON,
                codes.PROVIDER_NOT_IMPLEMENTED,
            )

        if not definition.configured:
            return decide(
                AuthorizationResult.DENIED,
                DENIED_NOT_CONFIGURED_REASON,
                codes.PROVIDER_REAL_UNAVAILABLE,
            )

        if not definition.is_approved_for_production:
            return decide(
                AuthorizationResult.DENIED,
                DENIED_NOT_HOMOLOGATED_REASON,
                codes.PROVIDER_NOT_HOMOLOGATED,
            )

        for rule in _RULES:
            if rule.matches(
                normalized_project, caller_role, normalized_environment, normalized_provider
            ):
                return decide(AuthorizationResult.ALLOWED, ALLOWED_REASON)

        return decide(
            AuthorizationResult.DENIED,
            DENIED_UNREGISTERED_REASON,
            codes.PROVIDER_NOT_AUTHORIZED_FOR_PROJECT,
        )

    def registered_combinations(self) -> list[dict[str, list[str]]]:
        """Projeção legível da matriz para diagnóstico e documentação."""
        return [
            {
                "project_ids": sorted(rule.project_ids),
                "caller_roles": sorted(role.value for role in rule.caller_roles),
                "environments": sorted(rule.environments),
                "providers": sorted(rule.providers),
                "notes": [rule.notes] if rule.notes else [],
            }
            for rule in _RULES
        ]


provider_authorization_service = ProviderAuthorizationService()
