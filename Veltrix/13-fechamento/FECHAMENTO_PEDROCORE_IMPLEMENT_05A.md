# Fechamento — PEDROCORE-IMPLEMENT-05A — Flags, guards e testes opt-in finais

## Implementado

- Guard central `apps/api/app/modules/real_features/service.py`: leitura dinâmica de flags de ambiente para OCR, multimodal, visual QA, Playwright e testes reais — **tudo `false` por padrão**. Duas flags de segurança com default **`true`**: `PEDROCORE_ENFORCE_PROJECT_POLICY` e `PEDROCORE_RELEASE_REQUIRE_HUMAN_REVIEW_FOR_REAL_FEATURES`.
- 28 warning codes novos em `contracts/codes.py` (testes reais desabilitados, OCR, multimodal, Playwright, FinGuard real, policy enforcement, release com recurso real) com severidades coerentes.
- Helper de testes opt-in `tests/real_flags.py` (`optin(FLAG)` → `pytest.mark.skipif`).
- `tests/test_real_optin.py`: 6 testes reais opt-in, todos **SKIPPED por padrão** (integração, FinGuard, provider real, OCR, multimodal, Playwright).
- `tests/test_real_feature_flags.py`: 6 testes provando default-off, defaults de segurança true, parsing estrito de "true" e allowlist de URLs.
- `.env.example`: 14 variáveis novas, sem valor real, sem tocar `.env`/`apps/api/.env`.

## Estratégia

Recurso real = opt-in + flag explícita + skipado no pytest padrão + revisão humana + sem efeito destrutivo. A flag só é aceita com o valor literal `true` (case-insensitive); qualquer outro valor mantém desabilitado.

## Garantias

Nenhum provider real, OCR, Playwright, multimodal ou FinGuard real executado; `.env`/`apps/api/.env`/`apps/web` intocados; nenhuma request externa.

---

## Navegacao

- [[MOC_FECHAMENTOS]]
- [[MOC_VELTRIX]]
