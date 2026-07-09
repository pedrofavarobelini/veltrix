# PedroCore - Perguntas e Respostas

Atualizado em: 09/07/2026

## 1. O que e o PedroCore?

E um core/orquestrador local de IA para centralizar providers, regras de seguranca, contexto de projeto, memoria tecnica e avaliacao no ecossistema de projetos.

## 2. Ele e uma IA propria?

Ele e uma camada propria de orquestracao e inteligencia operacional deterministica. Nao e um modelo treinado proprio.

## 3. Ele substitui Claude, OpenAI ou Gemini?

Nao. Ele pode orquestrar providers externos quando autorizado, mas por default usa mock/local_qa e bloqueia chamadas reais.

## 4. Como ele responde aos projetos?

Um sistema consumidor envia payload para `/api/orchestrate`. O PedroCore classifica a task, aplica policy, monta prompt, escolhe provider seguro e devolve resposta com warnings/audit.

## 5. O que e `local_qa`?

E um pseudo-provider local deterministico para QA textual. Ele nao e LLM e nao chama rede.

## 6. O que e `local_model`?

E o provider generativo local futuro. Hoje esta registrado, mas default-off, sem transport real e sem backend instalado.

## 7. Relatorios treinam o PedroCore?

Nao. Relatorios viram sinais e memoria tecnica. Isso e contexto, nao treinamento de pesos.

## 8. O que e Report Memory?

E uma memoria tecnica controlada, default off, que pode guardar snapshots de relatorios quando habilitada.

## 9. O que e Intelligence Layer?

E uma camada deterministica que monta um plano interno de resposta antes do provider, com instrucoes e flags de seguranca.

## 10. Como ele ajuda o FinGuard hoje?

Do lado PedroCore, aceita `origin_system=finguard` como consumidor read-only para algumas tasks. Ele nao le nem altera o FinGuard real.

## 11. O assistente FinGuard ja esta integrado?

Nao. A integracao real do assistente FinGuard via PedroCore e uma frente separada.

## 12. Como testar?

Rodar `uv run pytest`, `uv run python -m app.modules.eval_harness.run` e chamadas locais em `127.0.0.1`, sempre com `provider=mock` ou `local_qa` e `allow_real_provider=false`.

## 13. Quais sao os riscos?

Provider real autorizado manualmente pode chamar rede/custo; `local_model` ainda nao tem transport real; memoria persistente opt-in exige governanca; docs historicas podem ter ruido.

## 14. Ele executa comandos?

Nao. Policy Enforcement bloqueia semantica de execucao, escrita, delecao, migration, deploy, push e comandos em payload.

## 15. Ele faz QA automatico completo?

Nao. Ele faz analise textual local e release gate conservador. QA tecnico/E2E de cada produto continua no produto.

## 16. O que significa "finalizado localmente"?

Significa que, no estado local auditado, o core seguro/orquestrador esta implementado e validado por testes e rotas locais. Nao significa deploy, provider real liberado ou modelo proprio.

## 17. O que dizer em entrevista?

Explique que o projeto implementa uma arquitetura segura de orquestracao de IA: multi-provider, safe mode, fallback, policy, memoria tecnica default-off, local model preparado e eval harness. Diga explicitamente que nao ha fine-tuning nem modelo treinado proprio.

## 18. Como explicar para portfolio?

"PedroCore IA e um backend FastAPI de orquestracao segura de IA para projetos consumidores, com contratos, guardrails, QA textual local, release gate conservador e estudo de evolucao para memoria e modelo local opt-in."
