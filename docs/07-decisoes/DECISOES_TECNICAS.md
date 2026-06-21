# PedroCore IA — Decisões Técnicas

## Decisão 001 — Não treinar IA do zero

O projeto cria uma camada/orquestrador de IA, não um modelo próprio.

## Decisão 002 — Backend em Python

Python foi mantido por alinhamento com IA e aprendizado do usuário.

## Decisão 003 — Frontend em React + TypeScript

A interface continua simples, moderna e fácil de testar.

## Decisão 004 — V2 não será Gemini-only

A V2 entrega estrutura multi-provider completa inicial.

## Decisão 005 — Fallback obrigatório

Se qualquer provider real falhar, a resposta cai para MockProvider. Isso evita quebrar a interface.

## Decisão 006 — Chaves fora do código

Todas as API keys ficam somente no `.env`, nunca no GitHub ou no frontend.
