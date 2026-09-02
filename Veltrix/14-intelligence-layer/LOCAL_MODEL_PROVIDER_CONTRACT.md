# Local Model Provider — Contrato Futuro

Frente: `PEDROCORE-MODEL-FOUNDATION-01`
Atualizado em: 08/07/2026

Links: [[INTELLIGENCE_LAYER_OVERVIEW]] | [[../00_MAPEAMENTO_GERAL_PEDROCORE]]

Nota de status atual (09/07/2026): este documento registra o contrato criado em `PEDROCORE-MODEL-FOUNDATION-01`. A frente posterior `PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01` registrou `local_model` como provider opt-in default-off em `providers/local_model_provider.py`, ainda sem transport real. Ver [[LOCAL_MODEL_PROVIDER]].

## 1. O que é

Contrato estrutural para um **futuro provider generativo local** do Veltrix, definido em `apps/api/app/modules/providers/local_model_contract.py` (`LocalModelProviderContract`).

Nesta frente de fundação era **apenas contrato**: nenhuma chamada de rede, nenhum backend instalado, nenhum modelo baixado, nenhuma geração de texto.

## 2. local_model NÃO é local_qa

| | `local_qa` | `local_model` (futuro) |
|---|---|---|
| Natureza | determinístico (heurística QA) | generativo (LLM local) |
| Status | ativo no pipeline (`LOCAL_PROVIDERS`) | contrato de fundação; provider opt-in default-off registrado em frente posterior |
| Release gate | único provider confiável | nunca aprova sozinho |
| Rede | nenhuma | nenhuma (backend local) |
| Backend | código próprio | Ollama, llama.cpp, LM Studio ou custom |

No estado atual, pedir `provider="local_model"` passa pelo gate do provider opt-in: sem `allow_local_model=true`, sem flag/backend válido ou sem transport real, o resultado correto é fallback Mock seguro.

## 3. Campos do contrato

| Campo | Valor nesta frente |
|---|---|
| `provider_id` | `"local_model"` |
| `category` | `"local_generative"` |
| `real_provider` | `false` |
| `requires_external_api_key` | `false` (validação rejeita `true`) |
| `enabled_by_default` | `false` |
| `supports_streaming` | `false` |
| `supports_tools` | `false` |
| `max_context_tokens` | `null` |
| `backend` | `"ollama"` \| `"llama_cpp"` \| `"lm_studio"` \| `"custom"` |
| `endpoint_url` | `null` |
| `health_check_supported` | `false` |
| `generation_supported` | `false` (validação rejeita `true` nesta fundação) |

## 4. Regras absolutas desta frente

- Não implementar chamada real.
- Não instalar Ollama/llama.cpp/LM Studio.
- Não fazer request HTTP.
- Não baixar modelo.
- Na frente `PEDROCORE-MODEL-FOUNDATION-01`, não registrar `local_model` no `provider_registry` como provider funcional. Esta regra histórica foi sucedida por `PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01`, que registrou o provider default-off sem transport real.
- `local_model` não substitui providers externos: ele será uma opção adicional de orquestração.

## 5. Roadmap do provider local

A implementação operacional real ainda fica para frente futura de transport local, porque `PEDROCORE-LOCAL-MODEL-01` registrou o provider, mas não implementou HTTP/transport real. Ela exigirá no mínimo:

1. decisão humana de backend e instalação manual da dependência (Decisão 064 se aplica);
2. flag opt-in default-off (padrão `real_features`);
3. health check antes de geração;
4. sanitização de prompt/resposta;
5. `local_model` continua **fora** de `RELEASE_GATE_TRUSTED_PROVIDERS` — geração local não aprova release gate;
6. avaliação via Evaluation Foundation antes de qualquer uso operacional.

## 6. Testes

`apps/api/tests/test_local_model_contract.py` cobre: defaults desabilitados/offline, rejeição de `generation_supported=true`, rejeição de chave externa, backends permitidos e distinção `local_qa` vs `local_model`. A suíte posterior também cobre o provider registrado default-off em `apps/api/tests/test_local_model_provider.py`.
