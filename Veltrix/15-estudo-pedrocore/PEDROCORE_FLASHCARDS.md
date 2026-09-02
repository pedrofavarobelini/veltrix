# Veltrix - Flashcards

Atualizado em: 09/07/2026

Pergunta: O que e o Veltrix?
Resposta: Um core/orquestrador local de IA para centralizar providers, policy, contexto, memoria tecnica, QA e audit.

Pergunta: Veltrix e um modelo treinado?
Resposta: Nao. Ele orquestra IA e aplica regras; nao treina pesos.

Pergunta: Qual e o endpoint operacional principal?
Resposta: `POST /api/orchestrate`.

Pergunta: Qual endpoint preserva compatibilidade de chat?
Resposta: `POST /api/chat`.

Pergunta: Qual endpoint lista providers?
Resposta: `GET /api/providers`.

Pergunta: Quais rotas de memoria tecnica existem?
Resposta: `POST /api/reports/analyze`, `POST /api/reports/ingest` e `GET /api/project-memory/{project_id}/summary`.

Pergunta: O que e `allow_real_provider`?
Resposta: Flag do payload que autoriza provider real. Default e `false`.

Pergunta: O que acontece se provider real e pedido sem autorizacao?
Resposta: Safe mode bloqueia e aplica fallback Mock.

Pergunta: O que e `mock`?
Resposta: Provider local simulado usado como default/fallback seguro.

Pergunta: O que e `local_qa`?
Resposta: Pseudo-provider deterministico para QA textual e release gate.

Pergunta: `local_qa` chama rede?
Resposta: Nao.

Pergunta: O que e `local_model`?
Resposta: Provider generativo local futuro, registrado opt-in default-off, sem transport real.

Pergunta: `local_model` aprova release gate?
Resposta: Nao. Release gate confia somente em `local_qa`.

Pergunta: O que e `allow_local_model`?
Resposta: Flag explicita para permitir tentativa de uso do `local_model`.

Pergunta: O que acontece sem `allow_local_model=true`?
Resposta: `LOCAL_MODEL_NOT_AUTHORIZED` e fallback Mock.

Pergunta: O que e `context_from_memory`?
Resposta: Flag para tentar anexar snapshot de memoria tecnica ao prompt. Default `false`.

Pergunta: Report Memory e default on?
Resposta: Nao. Default off.

Pergunta: Relatorios treinam IA?
Resposta: Nao. Eles viram sinais e memoria tecnica.

Pergunta: Report Memory e RAG?
Resposta: Nao. RAG/embeddings ainda nao existem.

Pergunta: O que e Task Router?
Resposta: Modulo que classifica task, criticidade, estilo de resposta e permissao de mock.

Pergunta: O que e Project Context?
Resposta: Modulo que define limites por sistema consumidor, como Veltrix ou FinGuard.

Pergunta: Como FinGuard e tratado?
Resposta: Como consumidor read-only; Veltrix nao le nem altera o repositorio FinGuard.

Pergunta: O que e Policy Enforcement?
Resposta: Camada que bloqueia comandos, escrita, delecao, deploy, push e fluxos criticos indevidos.

Pergunta: O que e Prompt Builder?
Resposta: Modulo que monta o prompt enriquecido com contexto, artefatos, inteligencia e memoria opcional.

Pergunta: O que e Intelligence Layer?
Resposta: Plano deterministico de resposta e seguranca antes do provider.

Pergunta: Intelligence Layer chama provider?
Resposta: Nao.

Pergunta: O que e Eval Harness?
Resposta: Executor deterministico de casos que valida invariantes de seguranca.

Pergunta: Eval Harness e benchmark de LLM?
Resposta: Nao.

Pergunta: Quantos casos o eval harness atual validou na auditoria?
Resposta: 11 casos, todos passaram.

Pergunta: Qual foi o resultado do pytest na auditoria?
Resposta: `296 passed, 6 skipped, 2 warnings`.

Pergunta: O que e release gate?
Resposta: Avaliacao assistida para decidir se algo pode avancar, com regras conservadoras.

Pergunta: Quando release gate pode aprovar?
Resposta: Com evidencia textual limpa, risco baixo, confianca suficiente, sem fallback/safe mode e provider `local_qa`.

Pergunta: Provider real pode aprovar release gate sozinho?
Resposta: Nao.

Pergunta: Mock pode aprovar release gate?
Resposta: Nao.

Pergunta: O que e Artifact Reader?
Resposta: Leitor opt-in e allowlisted de arquivos; default off e proibido para FinGuard.

Pergunta: O que acontece com path em artifact por default?
Resposta: E rejeitado sem leitura.

Pergunta: `.env` foi tracked na auditoria?
Resposta: Nao. Apenas `apps/api/.env.example` apareceu tracked.

Pergunta: Qual branch foi auditada?
Resposta: `main`.

Pergunta: Qual HEAD foi auditado?
Resposta: `e0ff8e3`.

Pergunta: Qual tag representa o core operacional seguro finalizado localmente?
Resposta: `v7.0.0`.

Pergunta: Qual tag representa o MVP backend?
Resposta: `v6.0.0`.

Pergunta: O Veltrix ja esta integrado ao Assistente FinGuard real?
Resposta: Nao. Essa integracao e frente futura separada.

Pergunta: O Veltrix baixa modelo local?
Resposta: Nao.

Pergunta: O Veltrix instala Ollama, llama.cpp ou LM Studio?
Resposta: Nao.

Pergunta: O que significa `REPORT_MEMORY_IS_NOT_TRAINING`?
Resposta: Aviso de que relatorios nao treinam IA; geram apenas sinais/memoria tecnica.

Pergunta: O que significa `FINANCIAL_DISCLAIMER`?
Resposta: Aviso obrigatorio de resposta financeira conservadora, sem acao financeira.

Pergunta: O que significa `INTERNAL_AUTH_NOT_CONFIGURED`?
Resposta: API interna sem chave configurada, operando em modo local/dev.

Pergunta: O que significa `LOCAL_MODEL_NOT_AUTHORIZED`?
Resposta: `local_model` foi pedido sem `allow_local_model=true`.

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]]
- [[../MOC_VELTRIX]]
- [[PEDROCORE_GLOSSARIO]]
- [[PEDROCORE_PERGUNTAS_E_RESPOSTAS]]
