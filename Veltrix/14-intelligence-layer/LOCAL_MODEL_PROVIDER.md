# Local Model Provider — Opt-in

Frente: `PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01` (Fase C)
Atualizado em: 09/07/2026

Links: [[LOCAL_MODEL_PROVIDER_CONTRACT]] | [[../00_MAPEAMENTO_GERAL_PEDROCORE]] | [[EVAL_HARNESS]]

## 1. O que mudou em relação ao contrato (MODEL-FOUNDATION-01)

O contrato virou provider registrado: `apps/api/app/modules/providers/local_model_provider.py` (`LocalModelProvider`), presente no `provider_registry` como `local_model` — **default OFF**, `real_provider=false`, `configured=false` sem flag explícita.

**Nenhuma chamada de rede existe nesta frente**: o transport padrão é `None`; habilitar as flags sem um transport real resulta em fallback Mock controlado (`LOCAL_MODEL_TRANSPORT_UNAVAILABLE`). Testes usam fake transport injetado. A implementação do transport real (HTTP para backend local) é frente futura.

## 2. local_model ≠ local_qa (diferença obrigatória)

| | `local_qa` | `local_model` |
|---|---|---|
| Natureza | determinístico (heurística QA) | generativo (LLM local) |
| Release gate | **único confiável** | **nunca aprova** (fora de `RELEASE_GATE_TRUSTED_PROVIDERS`) |
| Ativação | sempre disponível | opt-in duplo (flag de ambiente + `allow_local_model` no payload) |
| Chave externa | nenhuma | nenhuma |

## 3. Condições cumulativas de uso

O `local_model` só executa quando **todas** valem:

1. `provider="local_model"` no payload;
2. `allow_local_model=true` no payload (senão `LOCAL_MODEL_NOT_AUTHORIZED`);
3. `PEDROCORE_ENABLE_LOCAL_MODEL=true` e backend válido (senão `LOCAL_MODEL_DISABLED`);
4. task não é `release_gate_review` nem criticidade `critical` (senão `LOCAL_MODEL_TASK_BLOCKED`);
5. task permitida pela policy do projeto.

`allow_real_provider` continua `false` — o local_model não usa e não destrava o safe mode. Qualquer falha → fallback Mock seguro.

## 4. Configuração (apenas `.env.example`; default OFF)

```text
PEDROCORE_ENABLE_LOCAL_MODEL=false
PEDROCORE_LOCAL_MODEL_BACKEND=disabled   # ollama | llama_cpp | lm_studio | openai_compatible_local | custom
PEDROCORE_LOCAL_MODEL_ENDPOINT="http://127.0.0.1:11434"
PEDROCORE_LOCAL_MODEL_NAME=""
PEDROCORE_LOCAL_MODEL_TIMEOUT_SECONDS=30
```

## 5. Como ativar futuramente (responsabilidade do operador)

1. Instalar manualmente um backend local (Ollama, llama.cpp, LM Studio ou compatível OpenAI local) — **nenhum download/instalação automática acontece**; nenhum modelo é baixado pelo Veltrix.
2. Configurar as flags acima no ambiente (nunca versionar `.env` real).
3. Aguardar/implementar a frente do transport real (hoje o transport é interface testável por fake).
4. Enviar `provider="local_model"` + `allow_local_model=true` por request.

## 6. Riscos e limites

- **Performance**: modelos locais dependem de hardware do operador; latência/qualidade variam por backend/modelo.
- **Qualidade**: `local_model` não substitui Claude/OpenAI/Gemini para tarefas críticas; release gate e decisões críticas continuam com `local_qa` + revisão humana.
- **Sem rede nesta frente**: qualquer teste padrão roda sem tocar rede; o teste opt-in real ficará atrás de flag própria quando o transport existir.

## 7. Testes

`apps/api/tests/test_local_model_provider.py`: disabled por padrão, bloqueio sem `allow_local_model`, flag off sem rede, fake transport com resposta normalizada, sem transport → fallback, bloqueio em release gate, fora de `RELEASE_GATE_TRUSTED_PROVIDERS`, independência de `allow_real_provider`.
