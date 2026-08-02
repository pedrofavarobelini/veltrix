# Fechamento — PEDROCORE-FINALIZE-06A — Enforcement final de policy e release gate

## Ponto fraco fechado

`allowed_tasks` deixou de ser apenas warning em fluxos críticos: o módulo `policy_enforcement` (introduzido na 05B, sob `PEDROCORE_ENFORCE_PROJECT_POLICY=true` por padrão) bloqueia de verdade — a requisição não chega ao provider, ao reader nem à análise.

## Regras finais de bloqueio

**Policy (antes de qualquer processamento):**
- task_type com semântica perigosa (executar/escrever/deletar/migrar/deploy/push/commit) → bloqueio **incondicional**, mesmo com enforcement desligado (testado);
- payload com chaves de comando em metadata/context → bloqueio incondicional;
- task crítica não permitida para o projeto → bloqueio (`FINGUARD_TASK_NOT_ALLOWED` para FinGuard);
- origem desconhecida em fluxo crítico → bloqueio;
- tasks não críticas fora da lista → warning (compatibilidade preservada).

**Release gate (decisão final):**
- somente `local_qa` (análise textual local determinística) pode aprovar (`RELEASE_GATE_TRUSTED_PROVIDERS`);
- provider real/externo → `RELEASE_REQUIRES_HUMAN_REVIEW`, nunca aprova sozinho — mesmo com `allow_real_provider=true`;
- mock/fallback → bloqueado (regra pré-existente);
- evidência visual-only, OCR-only ou plano exploratório-only → bloqueado (sem análise textual conclusiva);
- caminhos seguros continuam funcionando (teste ponta-a-ponta).

## Testes

`tests/test_release_hardening.py` (8) + os 11 de `test_finguard_enforcement.py` (05B). Total da suíte: `216 passed, 6 skipped, 2 warnings`.

## Compatibilidade

`/api/chat` legado intacto; todos os testes das fases anteriores continuam passando sem alteração.

---

## Navegacao

- [[MOC_FECHAMENTOS]]
- [[MOC_PEDROCORE_IA]]
