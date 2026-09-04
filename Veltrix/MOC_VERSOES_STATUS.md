# MOC Versoes Status

## ESTADO CORRENTE — 2026-09-03

Fechamento canônico: [[19-encerramento-final/VELTRIX_FINAL_FUNCTIONAL_GATE]].

| Eixo | Valor |
|---|---|
| Produto / UI | **V5.2.0** |
| API / backend | **0.2.0** |
| Tags Git | `v2.0.0` … `v7.0.0` — linha **independente**, não acompanha o produto |
| Final Functional Gate | **PASS** |
| Functional Freeze | **ACTIVE** |
| Publicação | **confirmada** — `github.com/pedrofavarobelini/veltrix`, Apache-2.0 |
| Aceite visual | `HUMAN_VISUAL_ACCEPTANCE = PASS` |
| Aceite em uso real | `HUMAN_RUNTIME_ACCEPTANCE = PASS` |

Nenhuma versão, tag ou release foi criada pelo Final Functional Gate: ele
corrigiu defeitos dentro de contratos já congelados.

Taxonomia completa dos três eixos: `VERSION.md` na raiz do repositório.

Tudo abaixo desta seção é **snapshot de checkpoint**: era verdade na data
indicada e não descreve o estado de hoje.

## SNAPSHOT DO CHECKPOINT — 2026-08-20

- [[19-encerramento-final/PEDROCORE_FECHAMENTO_DOCUMENTAL_FINAL_ERAS_1_A_3]]
- Era 1 PASS; Era 2 PASS; Era 3 FOUNDATION PASS / TRAINING DEFERRED.
- Zero candidatos reais autorizados; `DATASET_NOT_READY`.
- `924 passed, 7 skipped, 2 warnings`; Ruff global PASS; Pyright Era 3 sem erros.
- Fechamento documental sem alteração de versão, tag ou Git.

## SNAPSHOT DO CHECKPOINT — 2026-08-14

- [[17-multi-provider-safe-evolution/PEDROCORE_STRUCTA_CONSUMER_01]]
- [[17-multi-provider-safe-evolution/GATE_PEDROCORE_STRUCTA_CONSUMER_01]]
- Estado: Structa registrado como consumer de menor privilégio; Gate PASS
  offline; provider real default-off; nenhuma Etapa 13 executada.

Mapa de versao, status, changelog e fechamento.

## Documentos de estado

- `VERSION.md` (raiz do repositório)
- `README.md` (raiz do repositório)
- [[09_STATUS_ATUAL]]
- [[08_CHANGELOG]]
- [[19-encerramento-final/VELTRIX_FINAL_FUNCTIONAL_GATE]] — fechamento canônico atual
- [[17-veltrix/VELTRIX_FINAL_STATE]] — descrição arquitetural consolidada
- [[13-fechamento/FECHAMENTO_PEDROCORE_FINAL]]
- [[16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01]]
- [[00_MAPEAMENTO_GERAL_PEDROCORE]]
- [[15-estudo-pedrocore/PEDROCORE_AUDITORIA_STUDY_MAP_01]]
- [[15-estudo-pedrocore/PEDROCORE_VEREDITO_FINAL]]
- [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]]
- [[17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7]]
- [[18-provider-output-budget-cancellation/FECHAMENTO_PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]]
- [[18-provider-output-budget-cancellation/PEDROCORE_ASSISTANT_FINAL_CLOSURE_01]] — Assistente IA encerrado (3/4)
- [[19-encerramento-final/PEDROCORE_FECHAMENTO_DOCUMENTAL_FINAL_ERAS_1_A_3]]

## Tags e commits

- `v7.0.0` - fechamento tecnico local do core operacional seguro.
- `v6.0.0` - MVP backend em `ee2ac68679feea6ac108abba8726d11da101576c`.
- `d6106b7` - `PEDROCORE-QA-SAFETY-HARDENING-01`, endurecimento QA/safety sem reabrir core.
- `62beff1` - Etapa 1, catálogo de providers/modelos.
- `64e6c59` + `c67ec6a` - Etapa 2 e correção de credencial compartilhada.
- `be56a7e` - Etapa 3, provider/model binding.
- `d93a4ff` + `8c97004` + `0daa34b` - shadow mode e correção documental/técnica de modelos.
- `f7afff8` - Etapa 5, roteamento enforced com chamada única.
- `30d308f` - Etapa 6, health state e circuit breaker.
- `e389b2c` - Etapa 7, fallback real controlado.

Esses commits não criam nova tag nem alteram as versões V5.1.9, `0.2.0`, `v6.0.0` ou `v7.0.0`.

## Fechamentos

- [[13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01]]
- [[13-fechamento/PREPARACAO_TAG_V6_0_0]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_IMPLEMENT_03]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_IMPLEMENT_04]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_IMPLEMENT_05A]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_IMPLEMENT_05B]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_IMPLEMENT_05C]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_IMPLEMENT_05D]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_IMPLEMENT_05E]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_IMPLEMENT_05F]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_FINALIZE_06A]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_FINAL]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_ECOSYSTEM_INTELLIGENCE_SUITE_01]]
- [[16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01]]
- [[17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7]]

## Roadmap e decisoes

- [[03-versoes/ROADMAP]]
- [[07-decisoes/DECISOES_TECNICAS]]
