# PedroCore - Resumo Executivo

Atualizado em: 09/07/2026

## O que e o PedroCore

PedroCore IA e um core/orquestrador local de IA para o ecossistema de projetos do Pedro. Ele centraliza chamadas, politicas, contexto de projeto, fallback, avaliacao, memoria tecnica controlada e rotas de assistente, para que sistemas consumidores nao precisem falar diretamente com providers externos.

Ele nao e um modelo proprio treinado. Ele organiza, protege e audita o uso de IA.

## Por que foi criado

O objetivo e ter uma camada unica de controle para:

- padronizar chamadas de IA;
- bloquear provider real por padrao;
- separar sistemas consumidores, como FinGuard, do acesso direto a providers;
- permitir QA textual e release gate conservador;
- preparar memoria tecnica e modelo local futuro sem vender isso como treinamento;
- manter rastreabilidade via audit.

## Estado atual

Validacao local da auditoria:

- Branch `main`.
- HEAD `e0ff8e3`.
- Working tree inicial limpo.
- `apps/api/.env` nao tracked.
- Suite backend: `296 passed, 6 skipped, 2 warnings`.
- Eval harness: `11/11 passed`, exit code `0`.
- Rotas locais principais validadas em `127.0.0.1:3333`.

## O que ja faz

- Expoe API FastAPI: `/`, `/health`, `/api/chat`, `/api/providers`, `/api/orchestrate`, `/api/reports/analyze`, `/api/reports/ingest`, `/api/project-memory/{project_id}/summary`.
- Resolve task com Task Router.
- Resolve projeto com Project Context.
- Aplica Policy Enforcement antes de provider.
- Processa artefatos por payload e rejeita paths inseguros.
- Monta prompt enriquecido com Prompt Builder.
- Usa Mock fallback seguro.
- Bloqueia provider real por default (`allow_real_provider=false`).
- Roda QA textual local deterministica.
- Aplica release gate conservador.
- Gera audit em memoria na resposta.
- Analisa relatorios tecnicos como sinais, nao como treinamento.
- Registra `local_model` como provider opt-in default-off, ainda sem transport real.
- Roda eval harness deterministico com invariantes de seguranca.

## O que ainda nao faz

- Nao treina modelo.
- Nao faz fine-tuning.
- Nao faz RAG/embeddings.
- Nao baixa nem instala modelo local.
- Nao tem transport real do `local_model`.
- Nao chama provider real sem autorizacao explicita.
- Nao integra o assistente real do FinGuard pelo lado do FinGuard.
- Nao executa comandos em projetos externos.
- Nao le o repositorio real do FinGuard.

## Proximos passos

1. Commitar docs de auditoria/estudo se aprovado.
2. Planejar integracao real do Assistente FinGuard via PedroCore como frente separada.
3. Planejar transport real do `local_model` como opt-in, com teste real separado.
4. Configurar autenticacao interna antes de qualquer consumidor real.
5. Manter suite padrao sem provider real, sem rede externa e sem modelo local real.
