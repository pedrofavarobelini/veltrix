# PedroCore - Glossario

Atualizado em: 09/07/2026

## API

Interface HTTP que permite chamar o PedroCore. Exemplo: `POST /api/orchestrate`.

## Backend

Parte do sistema que roda no servidor. No PedroCore, o backend e FastAPI em Python.

## Provider

Servico ou modulo que gera resposta de IA. Pode ser mock, externo ou local.

## Provider real

Provider externo com chamada real, como Gemini, OpenAI, Claude, DeepSeek ou Grok. Fica bloqueado por default.

## Mock

Provider local simulado. Serve para desenvolvimento, fallback e testes sem rede.

## local_qa

Pseudo-provider local deterministico usado para QA textual e release gate. Nao e LLM e nao chama rede.

## local_model

Provider generativo local futuro. Hoje esta registrado como opt-in default-off, mas sem transport real. Nao e `local_qa`.

## Orchestrator

Camada que coordena task, projeto, policy, prompt, provider, QA, audit e resposta.

## Task Router

Modulo que classifica `task_type` e define criticidade, estilo de resposta e se mock e permitido.

## Project Context

Mapa de regras por sistema consumidor. Exemplo: FinGuard e read-only.

## Policy Enforcement

Camada que bloqueia tarefas perigosas antes de chamar provider.

## Prompt Builder

Modulo que monta o prompt final/enriquecido para o provider.

## Report Intelligence

Modulo que le um relatorio enviado por payload e extrai sinais deterministicos.

## Report Memory

Memoria tecnica controlada. Pode guardar sinais e snapshots quando habilitada. Default off.

## RAG

Recuperacao por busca/embeddings para anexar contexto. Nao existe no PedroCore atual.

## Fine-tuning

Treinar ou ajustar pesos de um modelo. O PedroCore nao faz isso.

## Treinamento

Processo de criar ou modificar um modelo de IA. Fora do escopo do PedroCore.

## Eval Harness

Executor de casos deterministos que verifica invariantes de seguranca e coerencia.

## Release Gate

Decisao assistida sobre avancar ou bloquear release. No PedroCore, so confia em `local_qa` com evidencia textual limpa.

## Audit

Registro em memoria dos metadados da request e da resposta. Nao e log persistente.

## Artifact Reader

Leitor opt-in de arquivos allowlisted. Default off, proibido para FinGuard e bloqueia `.env`.

## context_from_memory

Campo booleano do payload. Default `false`. Quando `true`, tenta anexar snapshot de memoria tecnica ao prompt.

## allow_real_provider

Campo booleano do payload. Default `false`. Quando `false`, provider real e bloqueado.

## allow_local_model

Campo booleano do payload. Default `false`. Sem ele, `local_model` cai em fallback seguro.

## Safe mode

Conjunto de bloqueios que evita chamada acidental a provider real e reduz risco em tarefas criticas.

## Warning code

Codigo padronizado que explica uma condicao de seguranca ou limite, como `FINANCIAL_DISCLAIMER` ou `LOCAL_MODEL_NOT_AUTHORIZED`.

## FinGuard como consumidor

Significa que o PedroCore aceita requests com `origin_system=finguard`, mas nao le nem altera o repositorio FinGuard.

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]]
- [[../MOC_PEDROCORE_IA]]
- [[../MOC_SEGURANCA]]
- [[../14-intelligence-layer/INTELLIGENCE_LAYER_OVERVIEW]]
