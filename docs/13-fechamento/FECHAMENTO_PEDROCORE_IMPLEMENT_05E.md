# Fechamento — PEDROCORE-IMPLEMENT-05E — QA visual multimodal opt-in (guard/contrato)

## Decisão

A arquitetura atual de providers é somente texto; enviar imagem a provider multimodal com segurança exigiria pipeline de sanitização visual inexistente. Conforme previsto pela frente, foi implementado **guard + contrato + warnings + testes de bloqueio + documentação da limitação** — nenhuma integração improvisada.

## Implementado

- `evaluate_real_visual_guard(allow_real_provider)` em `visual_qa/service.py`, com três condições cumulativas:
  1. `PEDROCORE_MULTIMODAL_PROVIDER_ENABLED=true` (senão `MULTIMODAL_PROVIDER_DISABLED`);
  2. `PEDROCORE_VISUAL_QA_ENABLED=true` (senão `MULTIMODAL_PROVIDER_REQUIRES_FLAG`);
  3. `allow_real_provider=true` no payload (senão `MULTIMODAL_PROVIDER_REQUIRES_EXPLICIT_AUTH`).
- Mesmo com as três condições satisfeitas, **o envio multimodal real não é executado nesta versão**: o guard retorna `REAL_FEATURE_REQUIRES_HUMAN_CONFIRMATION` e `provider_attempted` permanece `false`. Nenhuma imagem é enviada a provider externo em nenhuma hipótese, inclusive imagens com segredo.
- Guard integrado ao `visual_qa_analysis` do `/api/orchestrate`.

## Testes

`tests/test_multimodal_guard.py` (7): cada flag ausente bloqueia; auth ausente bloqueia; totalmente autorizado ainda exige confirmação humana e não executa; API reporta guard; pytest padrão nunca chama provider multimodal; release gate continua bloqueando visual mesmo com todas as flags. Teste real opt-in (`PEDROCORE_RUN_REAL_MULTIMODAL_TESTS`) skipado por padrão.

## Limitação documentada

QA visual real com provider multimodal fica para frente futura, com aprovação explícita, sanitização de imagem e revisão humana obrigatória — release gate jamais decide sozinho com base nisso.

---

## Navegacao

- [[MOC_FECHAMENTOS]]
- [[MOC_PEDROCORE_IA]]
