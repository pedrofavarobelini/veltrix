# MOC Multi-Provider Safe Evolution

Mapa oficial da evolução segura de providers, modelos, identidade, routing,
health e fallback do PedroCore.

## Fechamento consolidado

- [[17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7]] — fonte
  principal do estado técnico e operacional atual.
- Veredito: arquitetura multi-provider concluída; operação automática
  multi-provider ainda não, pois somente
  `gemini + gemini-3.5-flash` está homologado e elegível.
- Validação acumulada: `570 passed, 7 skipped, 2 warnings`; eval harness
  `14/14`, `risk_level="none"`.

## Encerramento do Assistente IA

- [[18-provider-output-budget-cancellation/PEDROCORE_ASSISTANT_FINAL_CLOSURE_01]]
  — auditoria residual, duas correções, homologação real única do Organizar e
  veredito de encerramento (**3/4**, limitação externa aceita).
- Correções: certeza de fechamento do transporte (`transport_close_outcome`) e
  preservação de `usage_metadata` no caminho de truncamento.
- Nenhuma nova frente do Assistente IA deve ser aberta.

## Evolução posterior

- [[18-provider-output-budget-cancellation/PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]]
  — orçamento de saída, timeout de transporte, cliente Gemini assíncrono,
  lifecycle e detecção de truncamento.
- [[18-provider-output-budget-cancellation/FECHAMENTO_PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]]
  — fechamento, limitações e riscos residuais.
- Efeito sobre as Etapas 6 e 7: o cancelamento local e o de transporte
  passaram a ser reais, mas o cancelamento **remoto** continua não
  comprovável. `completion_ambiguous` permanece obrigatório e timeout continua
  sem destravar retry, secundário ou fallback real.
- Validação após a frente: `703 passed, 7 skipped`; eval `14/14`.

## Etapas 1–7

- [[17-multi-provider-safe-evolution/ETAPA_1_CATALOGO_PROVIDERS]]
- [[17-multi-provider-safe-evolution/ETAPA_2_IDENTIDADE_AUTORIZACAO]]
- [[17-multi-provider-safe-evolution/ETAPA_3_PROVIDER_MODEL_BINDING]]
- [[17-multi-provider-safe-evolution/ETAPA_4_SHADOW_MODE]]
- [[17-multi-provider-safe-evolution/ETAPA_5_ROTEAMENTO_AUTOMATICO_CHAMADA_UNICA]]
- [[17-multi-provider-safe-evolution/ETAPA_6_HEALTH_STATE_CIRCUIT_BREAKER]]
- [[17-multi-provider-safe-evolution/ETAPA_7_FALLBACK_REAL_CONTROLADO]]

## Fixes críticos

- [[17-multi-provider-safe-evolution/FIX_CREDENCIAL_COMPARTILHADA]] —
  autenticado não significa identificado nem autorizado.
- [[17-multi-provider-safe-evolution/FIX_HOMOLOGACAO_CONFIGURACAO_MODELOS]] —
  configuração não cria modelo/homologação e adapter não recebe `model=None`.

## Arquitetura e segurança

- [[00_MAPEAMENTO_GERAL_PEDROCORE]]
- [[MOC_ARQUITETURA]]
- [[MOC_SEGURANCA]]
- [[16-qa-safety-hardening/PROVIDER_REAL_SAFETY]]
- [[16-qa-safety-hardening/MATRIZ_TASK_PROVIDER_POLICY]]
- [[07-decisoes/DECISOES_TECNICAS]]

## Testes, QA e observabilidade

- [[MOC_TESTES]]
- [[MOC_QA_RELEASE_GATE]]
- [[MOC_QA_SAFETY_HARDENING]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_OBSERVABILIDADE_LOCAL_01]]
- `apps/api/tests/test_provider_catalog.py`
- `apps/api/tests/test_caller_identity_authorization.py`
- `apps/api/tests/test_shared_credential_privilege.py`
- `apps/api/tests/test_provider_model_binding.py`
- `apps/api/tests/test_shadow_routing.py`
- `apps/api/tests/test_provider_routing_enforced.py`
- `apps/api/tests/test_provider_health_circuit_breaker.py`
- `apps/api/tests/test_provider_real_fallback_controlled.py`

## Status e histórico

- [[09_STATUS_ATUAL]]
- [[03-versoes/ROADMAP]]
- [[08_CHANGELOG]]
- [[MOC_VERSOES_STATUS]]

## Integração FinGuard

- [[MOC_INTEGRACOES]]
- [[11-integracoes/CONTRATO_FINGUARD_PEDROCORE]]
- [[11-integracoes/CONTRATO_FINGUARD_PEDROCORE_REAL_CONTROLADO]]

Contrato preservado:

```text
FinGuard → provider=auto → sem model → PedroCore controla a decisão
```

Não existe segundo provider real homologado/ativo para o FinGuard.

## Próximo passo

Primeiro decidir Claude versus OpenAI. Depois abrir uma única frente de
homologação controlada:

- `PEDROCORE-PROVIDER-HOMOLOGATION-CLAUDE-01`; ou
- `PEDROCORE-PROVIDER-HOMOLOGATION-OPENAI-01`.

Circuit breaker e fallback continuam default-off até haver evidência
operacional suficiente.
