# Fechamento — PEDROCORE-IMPLEMENT-05F — Playwright read-only opt-in

## Implementado

- Adapter `apps/api/app/modules/exploration/playwright_adapter.py` (`PlaywrightReadOnlyAdapter`, `PlaywrightExplorationResult`):
  - `PEDROCORE_EXPLORATION_PLAYWRIGHT_ENABLED=false` (padrão) → `PLAYWRIGHT_NOT_ENABLED`;
  - base URL fora de `PEDROCORE_EXPLORATION_ALLOWED_BASE_URLS` (ou allowlist vazia, ou URL contendo "finguard") → `PLAYWRIGHT_BASE_URL_NOT_ALLOWED`;
  - dependência não instalada → `PLAYWRIGHT_DEPENDENCY_UNAVAILABLE`, tratado sem falha (Playwright **não foi instalado** — instalação pesada requer aprovação explícita);
  - habilitado + allowlist + dependência instalada pelo humano → navegação **somente leitura** (título, status HTTP, até 50 links visíveis), headless, com `PLAYWRIGHT_READ_ONLY_MODE` + `PLAYWRIGHT_REQUIRES_HUMAN_REVIEW`;
  - métodos interativos (`click`, `type_text`, `submit`, `login`) **sempre** retornam `PLAYWRIGHT_ACTION_BLOCKED`, independentemente de flags — o adapter não possui caminho de escrita/interação;
  - `can_advance=false` e `requires_human_review=true` em qualquer resultado.

## Testes

`tests/test_playwright_guard.py` (8): desabilitado bloqueia; URL fora da allowlist bloqueia; URLs FinGuard sempre bloqueadas; allowlist vazia bloqueia tudo; dependência ausente tratada; ações interativas sempre bloqueadas; resultado nunca avança release; pytest padrão nunca abre navegador. Teste real opt-in (`PEDROCORE_RUN_REAL_PLAYWRIGHT_TESTS`) skipado por padrão.

## Garantias

Nenhum navegador aberto no pytest padrão; nenhuma dependência instalada; sem clique/digitação/submissão/login em qualquer configuração; FinGuard inacessível; release gate não avança com exploração.

---

## Navegacao

- [[MOC_FECHAMENTOS]]
- [[MOC_PEDROCORE_IA]]
