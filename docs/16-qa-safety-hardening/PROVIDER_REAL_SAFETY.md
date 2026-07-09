# Provider Real — Safety

## Providers reais estruturais

`gemini`, `openai`, `claude`, `deepseek`, `grok`
(`app/modules/providers/*_provider.py`, todos `real_provider=True`).
Existem como estrutura multi-provider; **nenhum é chamado por padrão**.

`mock` e `local_qa` são seguros (`real_provider=False`, sem chave, sem rede).
`local_model` é generativo local opt-in com contrato pronto e **transport
ausente** — sem transport injetado, não existe caminho de rede.

## Bloqueio por padrão

- `allow_real_provider=false` é default no schema (`ChatRequest`) e ausência
  do campo se comporta como `false`.
- Com a flag `false`, provider real vira fallback mock controlado com
  `safe_mode_blocked=true`, `error_code=PROVIDER_REAL_BLOCKED` — nunca 5xx,
  nunca stack trace.
- Payload aninhado (`context`/`metadata`/campo extra no JSON) não ativa a flag.
- Em tarefa crítica (`release_gate_review`), o bloqueio vira `status=blocked`
  e o release gate não avança.

## local_qa como release gate

`local_qa` é o único provider confiável para `release_gate_review`:
determinístico, sem chave, sem rede, baseado no analisador textual local.
Mock, provider real bloqueado e local_model **nunca** aprovam release gate.

## Riscos que o bloqueio elimina

- **Rede**: chamada externa não intencional em teste/CI.
- **Custo**: consumo de API paga sem autorização humana.
- **Chaves**: dependência/exposição de `*_API_KEY`; mock e local_qa operam
  sem chave alguma, e a chave interna de auth nunca é ecoada em erro 401.

## Guard estrutural de testes (novo nesta frente)

`apps/api/tests/conftest.py` substitui, em toda a suíte padrão,
`generate_response` dos 5 providers reais por um guard que:

1. registra a invocação e levanta `RuntimeError`
   (`REAL_PROVIDER_CALL_BLOCKED_BY_TEST_GUARD`) antes de qualquer SDK/rede;
2. **falha o teste no teardown** se houve invocação não marcada — mesmo que o
   pipeline tenha absorvido o erro via fallback;
3. se desativa apenas com `PEDROCORE_RUN_REAL_PROVIDER_TESTS=true`
   (opt-in humano já existente para `test_real_optin.py`).

Consequência: nem `allow_real_provider=true` dentro de um teste alcança a rede.

## Testes relacionados

- `tests/test_provider_real_safety.py` — default ausente = false; 5 providers
  bloqueados; provider inválido padronizado; bypass aninhado inócuo;
  mock/local_qa sem chave; guard disparando por invocação direta e via API
  autorizada; eval harness sem provider real.
- `tests/test_safe_mode.py` — bloqueio via `/api/chat` (pré-existente).
- `tests/test_policy_negative_cases.py` — falha de policy nunca chama provider.
- Fixtures de eval: `release-gate-blocks-real-provider`,
  `local-model-disabled-no-network`, `invalid-provider-falls-back-safely`.

## Links relacionados

- [[../MOC_QA_SAFETY_HARDENING]]
- [[MATRIZ_TASK_PROVIDER_POLICY]]
- [[RELEASE_GATE_CHECKLIST]]
- [[../MOC_SEGURANCA]]
- [[../00_MAPEAMENTO_GERAL_PEDROCORE]]
