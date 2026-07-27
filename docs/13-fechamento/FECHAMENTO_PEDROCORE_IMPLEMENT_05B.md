# Fechamento — PEDROCORE-IMPLEMENT-05B — Integração FinGuard controlada (lado PedroCore)

## Implementado

- Novo módulo `apps/api/app/modules/policy_enforcement/` (`PolicyEnforcementResult`, `PolicyEnforcementService.evaluate`): bloqueio **real** (não apenas warning) para task_type perigoso (execução/escrita/deleção/migração/deploy/push/commit), payload com chaves de comando, task crítica não permitida para o projeto e origem desconhecida em fluxo crítico. Controlado por `PEDROCORE_ENFORCE_PROJECT_POLICY` (default `true`).
- `OrchestrationService`: curto-circuito `_policy_blocked_outcome` — requisição bloqueada nunca chega ao provider, ao Artifact Reader nem à análise QA (`status="blocked"`, `provider_used="none"`, `error_code=PROJECT_POLICY_BLOCKED`/`FINGUARD_TASK_NOT_ALLOWED`, audit não persistente com `status=blocked`).
- `pedrocore` passou a permitir as tasks QA (uso local legítimo pelo próprio dono); tasks críticas de origens não autorizadas continuam bloqueadas.
- Contrato final documentado em `docs/11-integracoes/CONTRATO_FINGUARD_PEDROCORE_REAL_CONTROLADO.md`.
- 11 testes novos em `tests/test_finguard_enforcement.py` + opt-in `test_real_finguard_contract_roundtrip` (skipado por padrão).

## Garantias

FinGuard permanece read-only: sem comandos, sem escrita, sem leitura de path real, sem reader, sem provider real por padrão. `/api/chat` legado intacto (teste dedicado). Nenhum acesso real ao FinGuard no pytest padrão.

---

## Navegacao

- [[MOC_FECHAMENTOS]]
- [[MOC_PEDROCORE_IA]]
