from __future__ import annotations

from dataclasses import dataclass

from app.modules.risk_engine.pre_execution_schemas import DeterministicRuleMatch
from app.modules.risk_engine.schemas import OperationKind, RiskRequest, RiskSeverity

RULESET_VERSION = "deterministic-rules-v1"


@dataclass(frozen=True)
class _Rule:
    rule_id: str
    category: str
    severity: RiskSeverity
    reason_code: str
    terms: tuple[str, ...] = ()
    operations: tuple[OperationKind, ...] = ()


_RULES = (
    _Rule("database_migration", "migration", RiskSeverity.CRITICAL, "DATABASE_MIGRATION", ("migration", "migrate", "migração"), (OperationKind.MIGRATE,)),
    _Rule("schema_change", "migration", RiskSeverity.HIGH, "SCHEMA_CHANGE", ("schema", "ddl", "alter table")),
    _Rule("auth_authz", "security", RiskSeverity.CRITICAL, "AUTH_AUTHZ_CHANGE", ("auth", "authorization", "permission", "rbac", "oauth")),
    _Rule("secrets_env", "security", RiskSeverity.CRITICAL, "SECRETS_OR_ENV", (".env", "secret", "credential", "api key", "token")),
    _Rule("ci_cd", "operational", RiskSeverity.HIGH, "CI_CD_CHANGE", ("ci/cd", "workflow", "pipeline", "github actions")),
    _Rule("delete", "data", RiskSeverity.CRITICAL, "DELETE_OPERATION", ("delete", "drop", "remove", "excluir", "apagar"), (OperationKind.DELETE,)),
    _Rule("mass_file_change", "scope", RiskSeverity.HIGH, "MASS_FILE_CHANGE", ("mass change", "bulk", "all files", "todos os arquivos")),
    _Rule("security_policy", "security", RiskSeverity.CRITICAL, "SECURITY_POLICY_CHANGE", ("security policy", "access policy", "firewall", "waf")),
    _Rule("production_config", "operational", RiskSeverity.CRITICAL, "PRODUCTION_CONFIGURATION", ("production", "produção", "prod config")),
    _Rule("permissions", "security", RiskSeverity.HIGH, "PERMISSION_CHANGE", ("permission", "privilege", "role", "permissão")),
    _Rule("external_integration", "operational", RiskSeverity.HIGH, "EXTERNAL_INTEGRATION", ("webhook", "external integration", "third-party", "integração externa")),
)


def evaluate_deterministic_rules(request: RiskRequest) -> list[DeterministicRuleMatch]:
    haystack = " ".join(
        (
            request.request_text,
            " ".join(request.requested_operation.targets),
            " ".join(request.requested_operation.expected_changes),
            " ".join(request.requested_operation.commands),
            request.environment,
        )
    ).lower()
    matches: list[DeterministicRuleMatch] = []
    for rule in _RULES:
        term_match = bool(rule.terms) and any(term in haystack for term in rule.terms)
        operation_match = request.requested_operation.kind in rule.operations
        external_match = (
            rule.rule_id == "external_integration"
            and request.requested_operation.external_effects
        )
        mass_match = rule.rule_id == "mass_file_change" and len(request.requested_operation.targets) >= 20
        production_match = rule.rule_id == "production_config" and request.environment.lower() in {"prod", "production"}
        if term_match or operation_match or external_match or mass_match or production_match:
            matches.append(
                DeterministicRuleMatch(
                    rule_id=rule.rule_id,
                    rule_version=RULESET_VERSION,
                    category=rule.category,
                    severity=rule.severity,
                    reason_code=rule.reason_code,
                )
            )
    return matches
