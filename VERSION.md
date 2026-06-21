# PedroCore IA — Versionamento

Atualizado em: 20/06/2026 23:51:27

## Versão atual

V2 — Multi-provider com Gemini real

## Status

APROVADA

## Local oficial

C:\Projetos\pedrocore-ia

## Resumo da V2

A V2 implementou a arquitetura multi-provider do PedroCore IA e validou o primeiro provider real: Gemini.

## Entregas concluídas

- ProviderRegistry.
- Base multi-provider.
- MockProvider funcional.
- GeminiProvider funcional.
- Estrutura para OpenAI, Claude, DeepSeek e Grok.
- Endpoint /api/providers.
- Endpoint /api/chat com seleção de provider.
- Fallback para MockProvider.
- GEMINI_API_KEY configurada.
- Gemini testado com sucesso.
- Frontend validado.
- Documentação atualizada.

## Próxima versão

V3 — Histórico simples + gostei/não gostei salvo.

## Roadmap

- V1 — Chat simples + API mock. APROVADA.
- V1.0.4 — Correção definitiva dos textos da interface. APROVADA.
- V2 — Multi-provider com Gemini real. APROVADA.
- V3 — Histórico simples + gostei/não gostei salvo.
- V4 — Prompts por modo/projeto.
- V5 — API interna para conexão com FinGuard.
- V6 — PostgreSQL + logs.
- V7 — RAG/memória com documentos.
- V8 — Multi-provider avançado/refinado.
- V9 — Deploy/documentação final.
