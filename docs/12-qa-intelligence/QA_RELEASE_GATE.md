# QA Intelligence — Release Gate Assistido (`release_gate_review`)

> Nota DOCFIX: este caso de uso foi implementado no lado PedroCore em `POST /api/orchestrate` e `/api/chat`, usando `task_type="release_gate_review"`. O release gate é conservador e só aprova com `local_qa` + evidência textual limpa; não executa merge, deploy, tag ou teste.

## Objetivo

Apoiar a decisão de "esta frente pode avançar (ex.: para release)" com base em evidências de QA já produzidas — **apoio à decisão, nunca decisão automática**.

## Entrada esperada

- `message` — pedido de revisão (ex.: "esta frente pode avançar para release?").
- `artifacts` — relatórios de QA, resultados de smoke/E2E, `json_result`, `changelog`, `pending_list`, o que estiver disponível como evidência.
- `context` — recomendado incluir `project`, `environment` e `module`.

## Saída esperada

Resposta estruturada completa (ver `QA_INTELLIGENCE_OVERVIEW.md`, seção 6), com ênfase em:

- `can_advance` — a recomendação central deste caso de uso.
- `risk_level` — para justificar a recomendação.
- `failures` e `probable_causes` — quando `can_advance: false`, para explicar o porquê.
- `confidence` — refletindo a qualidade e completude das evidências recebidas.

## Regra de avanço/bloqueio (`can_advance`)

- **`can_advance: true`** quando os testes principais passam, as falhas identificadas são não bloqueantes e as evidências são suficientes.
- **`can_advance: false`** quando há falha crítica, relatório incompleto, fallback Mock em tarefa crítica, evidência insuficiente, risco de banco/dados/segurança, ou teste essencial falhou.

**O PedroCore não decide sozinho. O PedroCore recomenda; o usuário/desenvolvedor aprova.** Nenhum merge, deploy ou tag é criado ou disparado automaticamente a partir desta resposta — a ação de release permanece sempre uma decisão humana, executada fora do PedroCore.

## Exige resposta estruturada?

Sim, obrigatoriamente — este é o caso de uso mais crítico entre os documentados, dado que orienta uma decisão de avanço.

## Mock pode ser usado?

Apenas para teste, **nunca para uma decisão real de release**.

## Fallback Mock deve bloquear conclusão?

Sim, obrigatoriamente. Se `fallback_used: true`, a resposta deve ser `can_advance: false` e `status: "blocked"` — um release gate nunca pode ser liberado (`can_advance: true`) a partir de uma resposta simulada.

## Observações de segurança

- Este caso de uso é o de maior sensibilidade entre os documentados: uma recomendação equivocada de `can_advance: true` poderia induzir a avançar uma frente com risco real (ex.: dados financeiros incorretos, falha de segurança).
- Por isso, a regra de bloqueio por fallback é mais rígida aqui do que em `qa_report_analysis` ou `qa_failure_diagnosis`: qualquer incerteza deve pender para `can_advance: false` e `risk_level` mais alto, nunca o contrário.
- O PedroCore nunca executa a ação de "avançar" (merge, deploy, tag) — apenas recomenda textualmente através da resposta estruturada.
- Este caso de uso nunca acessa o repositório do FinGuard diretamente para verificar o estado real do código ou dos testes — depende inteiramente das evidências enviadas no payload pelo sistema de origem.

## Links relacionados

- [[../MOC_QA_RELEASE_GATE]]
- [[../MOC_QA_SAFETY_HARDENING]]
- [[../16-qa-safety-hardening/RELEASE_GATE_CHECKLIST]]
- [[../16-qa-safety-hardening/PROVIDER_REAL_SAFETY]]
