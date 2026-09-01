# PedroCore IA — Encerramento final

> **Checkpoint histórico do encerramento do core.** O core aqui descrito
> permanece encerrado no próprio escopo. O estado consolidado posterior das
> Eras 1–3 está em
> [[PEDROCORE_FECHAMENTO_DOCUMENTAL_FINAL_ERAS_1_A_3]] e prevalece para testes,
> Operational Intelligence, Risk Engine e Training Foundation.

Frente: `FINGUARD-PEDROCORE-CANONICAL-REPLAY-DOCS-GRAPH-FINALIZE-01`.

Status: **CANÔNICO ATUAL**. Este documento descreve o estado final do PedroCore
IA como core operacional concluído. Fechamentos anteriores continuam válidos
sobre o próprio escopo e são **históricos** — ver [[MOC_FECHAMENTOS]].

Voltar para a entrada do grafo: [[MOC_PEDROCORE_IA]].

---

## 1. Veredito

```text
PEDROCORE ENCERRADO — CORE OPERACIONAL CONCLUÍDO
```

Nenhuma implementação obrigatória permanece.

## 2. Objetivo original

Orquestrar múltiplos providers de IA por trás de um contrato único e seguro,
para que sistemas consumidores — o [[MOC_INTEGRACOES|FinGuard]] em primeiro
lugar — obtenham resposta de IA **sem** possuir chave de provider, sem escolher
modelo e sem depender de um fornecedor específico.

## 3. Arquitetura final

Pipeline central em `app/modules/orchestration/service.py`, na ordem real de
execução:

```text
identidade do caller       credencial -> projeto -> papel -> ambiente
validação de origem        origin_system e alegação, nunca identidade
project context + policy   task permitida para o projeto
intelligence plan          plano determinístico interno
shadow / enforced routing  motor único de decisão
provider/model binding     provider e modelo validados como UNIDADE
artifacts                  allowlist, sem leitura do repositório consumidor
prompt builder             prompt final
output budget              min(global, modelo, task)
transport timeout          sempre menor que o da orquestração
provider                   UMA chamada lógica, sem retry
normalização               finish_reason + usage_metadata reais
QA textual + release gate   decisão determinística local
auditoria + observabilidade projeção sanitizada
```

Detalhamento em [[MOC_ARQUITETURA]] e [[00_MAPEAMENTO_GERAL_PEDROCORE]].

## 4. Integração com o FinGuard

- Contrato entre sistemas: [[11-integracoes/CONTRATO_FINGUARD_PEDROCORE]] e
  [[11-integracoes/CONTRATO_FINGUARD_PEDROCORE_REAL_CONTROLADO]].
- O FinGuard é **consumidor comum**: envia `provider=auto`, **não** envia
  modelo e **não** possui `GEMINI_API_KEY`.
- O contrato público que chega à SPA do FinGuard é exatamente
  `{answer, suggestions, disclaimer}`. Nenhum metadado técnico atravessa.
- Homologação real do Assistente IA: **4/4** — ver §10.

## 5. Providers e modelos

| Provider | Adapter | Categoria | Homologação | Auto |
| --- | --- | --- | --- | --- |
| `gemini` | `GeminiProvider` | real externo | **homologado real** | **sim** |
| `claude` | `ClaudeProvider` | real externo | não homologado | não |
| `openai` | `OpenAIProvider` | real externo | não homologado | não |
| `deepseek` | `DeepSeekProvider` | real externo | não homologado | não |
| `grok` | `GrokProvider` | real externo | não homologado | não |
| `mock` | `MockProvider` | simulado | interno | não |
| `local_qa` | pseudo-provider | determinístico local | interno | não |
| `local_model` | `LocalModelProvider` | generativo local | não homologado | não |

Modelo homologado: `gemini-3.5-flash`, `max_output_tokens=8192`.

**Arquitetura multi-provider concluída; operação multi-provider automática não**,
porque existe apenas um par provider/modelo homologado e elegível. Isso é uma
decisão de homologação, não uma pendência de implementação.
Ver [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]].

## 6. Identidade e autorização

Ordem soberana: **credencial → registro → projeto → papel → ambiente**.

- Credencial registrada em `PEDROCORE_CALLER_REGISTRY` ⇒ identidade
  `registered`, projeto confiável, provider real autorizável.
- API key global ⇒ identidade `ambiguous`, projeto `shared_or_unknown` e
  **nenhum** provider real. Compatibilidade transitória.
- Registro ilegível ⇒ **fail-closed**: nenhuma identidade é derivada.
- Comparação de credencial por `hmac.compare_digest`.
- Consumidor comum não seleciona provider nem modelo.
- Divergência de origem é **rejeitada**, nunca corrigida em silêncio.

Ver [[MOC_SEGURANCA]] e [[17-multi-provider-safe-evolution/ETAPA_2_IDENTIDADE_AUTORIZACAO]].

## 7. Orçamento de saída

`effective_budget = min(global_cap, model_cap, task_cap)`, função pura.

- Teto global de segurança: `8192`.
- Task conversacional/financeira: `4096`.
- Task estruturada: `3072`.
- Task não catalogada: `2048` — o menor teto, nunca o global.
- O consumidor **nunca** participa: `ChatRequest` não tem campo de tokens.

## 8. Timeout e cancelamento

- Cliente Gemini **assíncrono nativo** (`client.aio`): cancelar a task cancela
  o `await` de verdade.
- `HttpOptions.timeout` explícito, derivado para expirar **antes** da espera da
  orquestração, com folga determinística.
- `HttpRetryOptions` **nunca** configurado: uma chamada lógica produz no máximo
  um dispatch externo.
- Truncamento detectado por `finish_reason=MAX_TOKENS` — evidência explícita do
  provider, jamais inferida do tamanho do texto.
- Fechamento do transporte é registrado como fato distinto:
  `confirmed` | `failed` | `not_attempted`.

### Limite honesto e permanente

**Fechar a conexão local não prova que a geração remota parou.** Timeout de
transporte permanece conclusão **ambígua** (`completion_ambiguous`). Isto é uma
limitação aceita e documentada, não uma pendência.

Ver [[18-provider-output-budget-cancellation/FECHAMENTO_PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]].

## 9. QA

- Suíte integral: **736 passed, 7 skipped** (medida nesta frente, após todas as
  alterações).
- Eval harness: **14/14**, `risk_level="none"`.
- Provider real **estruturalmente bloqueado** na suíte padrão por
  `tests/conftest.py`: cada adapter real é substituído por guard, e o teste
  falha no teardown se algum foi invocado.
- Grafo documental validado por `test_docs_graph.py` — ver §11.

Ver [[MOC_TESTES]] e [[MOC_QA_RELEASE_GATE]].

## 10. Assistente IA do FinGuard — 4/4

A homologação real do Assistente IA foi **consolidada em 4/4** nesta frente.

| Cenário | Origem da evidência |
| --- | --- |
| Quitar dívidas | evidência real anterior (aprovada) |
| Economizar | evidência real anterior (aprovada) |
| Crescer | evidência real anterior (aprovada) |
| **Organizar** | **evidência real nova, executada nesta frente** |

O Organizar era a última limitação aberta. Resultado da execução nova:
`provider_effective=gemini`, `model=gemini-3.5-flash`, `fallback=false`,
`retry=0`, **um** dispatch externo, `23.049 ms`.

A limitação anterior — causa indeterminada por observabilidade volátil — foi
**resolvida na origem**: o replay canônico do FinGuard agora persiste o
diagnóstico em disco antes do teardown.

Ver [[18-provider-output-budget-cancellation/PEDROCORE_ASSISTANT_FINAL_CLOSURE_01]].

## 11. Documentação e grafo

O vault do PedroCore é validado estruturalmente, não visualmente:

```powershell
cd apps\api
.venv\Scripts\python.exe -m app.modules.docs_graph.service
```

Sai com código diferente de zero diante de órfão, beco sem saída, link
quebrado, link ambíguo, basename duplicado ou documento inalcançável a partir
do MOC raiz [[MOC_PEDROCORE_IA]].

`.obsidian/graph.json` **não** é usado como prova: é configuração visual.

Hubs: [[MOC_HISTORICO_PEDROCORE]] e [[MOC_FECHAMENTOS]].

## 12. Git

- Branch: `main`. Sem push, sem tag, sem merge, sem rebase, sem amend nesta
  frente.
- Tags existentes: `v6.0.0` (MVP backend) e `v7.0.0` (fechamento técnico local
  do core). Ambas permanecem válidas como marcos.

## 13. Estado final

```text
core operacional              concluído
integração FinGuard           concluída e homologada 4/4
provider/model binding        concluído
identidade registrada         concluída
safe mode                     concluído
output budget                 concluído
timeout de transporte         concluído
cliente Gemini assíncrono     concluído
cancelamento local            tratado honestamente
cancelamento remoto           não comprovável (limitação aceita)
QA                            aprovado
grafo documental              íntegro
pendência obrigatória         nenhuma
```

## 14. Evoluções futuras opcionais

Nenhuma delas é pendência:

- homologar um segundo provider real (Claude ou OpenAI), por decisão explícita;
- ativar o provider generativo local, hoje opt-in e sem transporte padrão;
- persistir observabilidade além do ring buffer em memória;
- medir custo real em tokens numa execução autorizada;
- push para repositório remoto e deploy — decisões humanas.

## 15. O que não deve ser reaberto

- Arquitetura multi-provider — concluída.
- Identidade, autorização e binding — concluídos.
- Orçamento de saída e timeout de transporte — concluídos.
- Assistente IA do FinGuard — encerrado em 4/4.
- Cancelamento remoto — limitação aceita, não defeito.
- Bloco 12 (dashboard/logs/admin) — cancelado por decisão de produto.

## Hubs relacionados

- [[MOC_PEDROCORE_IA]] — entrada do grafo.
- [[MOC_FECHAMENTOS]] — todos os fechamentos.
- [[MOC_VERSOES_STATUS]] — versões e status.
- [[MOC_SEGURANCA]] — segurança e políticas.
- [[MOC_INTEGRACOES]] — contratos com o FinGuard.
