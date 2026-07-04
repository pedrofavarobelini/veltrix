# Objetivo do PedroCore IA

> Documento oficial de objetivos. Substitui a leitura do PedroCore como "assistente pessoal de testes" (escopo antigo da V1).

## Objetivo principal

Ser o **orquestrador central de IA do ecossistema de projetos Pedro**: receber mensagem, contexto e tipo de tarefa de sistemas (internos ou externos), decidir a estratégia de resposta, selecionar o provider/modelo adequado e executar a chamada correspondente.

## Objetivo secundário

Devolver uma **resposta padronizada** para o sistema de origem, de forma previsível e consistente, independentemente de qual provider foi usado internamente para gerá-la.

## Objetivo futuro (planejado, não implementado)

Apoiar casos de **inteligência operacional**:

- Análise de relatórios, logs, documentos e evidências de outros projetos.
- Apoio à parte exploratória/visual/inteligente do QA Automation de projetos externos, como o FinGuard.
- Leitura somente-leitura de artefatos Markdown/documentação (ex.: relatórios de QA, notas Obsidian), sem qualquer escrita nos sistemas de origem.

Esses itens são objetivos futuros de planejamento; nenhum foi implementado até esta etapa (`PEDROCORE-REPLAN-01A`).

## Objetivos fora do escopo atual

- Calcular números financeiros oficiais de qualquer sistema externo (isso permanece exclusivamente no sistema de origem, ex.: FinGuard).
- Alterar, rodar migrations, seed/reset, testes ou comandos dentro de qualquer projeto externo, incluindo o FinGuard.
- Substituir o QA Automation do FinGuard (validação de API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E) — esse subsistema permanece interno ao FinGuard.
- Redesenhar frontend, layout ou identidade visual durante a reformulação documental/arquitetural em curso.
- Prometer ou implementar integração já pronta com o FinGuard ou qualquer outro sistema externo.

## Histórico do objetivo original (V1)

A V1 tinha como foco validar interface de conversa, estrutura de backend, fluxo de envio/recebimento e organização de código, como base para evoluir para uma API de IA. Esse objetivo inicial foi cumprido e superado: o projeto evoluiu de "chat pessoal de testes" para "orquestrador central de IA", conforme descrito acima.
