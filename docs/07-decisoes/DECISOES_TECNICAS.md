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

## Decisão 007 — PedroCore IA como orquestrador central de IA do ecossistema Pedro

O PedroCore deixa de ser documentado apenas como chat pessoal e passa a ser a camada central de orquestração de IA para os projetos do ecossistema Pedro: recebe mensagem/contexto/tipo de tarefa, escolhe estratégia, seleciona provider/modelo e devolve resposta padronizada.

## Decisão 008 — Sistemas externos devem consumir IA preferencialmente via PedroCore

A direção estratégica é que outros sistemas do ecossistema Pedro consumam capacidades de IA através do PedroCore, em vez de integrarem provedores diretamente. Essa integração ainda não está implementada; é objetivo futuro.

## Decisão 009 — FinGuard é projeto externo e não deve ser alterado pelo PedroCore

O FinGuard permanece um repositório e sistema independentes. O PedroCore não altera código, dados, configuração ou documentação do FinGuard.

## Decisão 010 — QA Automation do FinGuard permanece dentro do FinGuard

A validação técnica (API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E, relatórios e evidências) é e continua sendo um subsistema interno do FinGuard. O PedroCore não reimplementa nem substitui essa validação.

## Decisão 011 — IA exploratória/visual do QA será caso de uso futuro do PedroCore

Apenas a parte de IA exploratória/visual/inteligente do QA Automation do FinGuard foi delegada ao PedroCore, como caso de uso futuro (QA Intelligence). Não implementado nesta etapa.

## Decisão 012 — PedroCore não calcula números financeiros oficiais de sistemas externos

O PedroCore pode, no futuro, explicar, resumir e sugerir a partir de artefatos e dados lidos, mas nunca substitui os cálculos financeiros oficiais de sistemas como o FinGuard.

## Decisão 013 — Providers reais exigem controle explícito para evitar chamadas acidentais

A ausência de chave de API não pode ser o único mecanismo de proteção contra chamadas reais acidentais. Providers reais devem ter, no planejamento técnico futuro, um controle explícito (ex.: flag de ambiente ou confirmação) antes de serem acionados, especialmente em fluxos automatizados ou testes.

## Decisão 014 — Fallback Mock não pode validar tarefas críticas silenciosamente

O fallback automático para `MockProvider` é aceitável para preservar a experiência de chat, mas não pode ser usado, no futuro, para "validar" silenciosamente tarefas críticas de sistemas externos (ex.: análises de QA). Qualquer consumidor crítico deve checar explicitamente `fallback_used` antes de considerar uma resposta como real.

## Decisão 015 — Frontend/design ficam congelados durante a reformulação arquitetural

Durante a frente `PEDROCORE-REPLAN-01` (consolidação documental, planejamento técnico e arquitetura-alvo), nenhuma mudança de frontend, layout, tema, identidade visual ou componente é realizada. O frontend permanece na V5.1.9 até que a reformulação documental/arquitetural seja concluída.
