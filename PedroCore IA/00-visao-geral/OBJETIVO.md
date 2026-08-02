# Objetivo do PedroCore IA

> Documento oficial de objetivos. Substitui a leitura do PedroCore como "assistente pessoal de testes" (escopo antigo da V1).

## Objetivo principal

Ser o **orquestrador central de IA do ecossistema de projetos Pedro**: receber mensagem, contexto e tipo de tarefa de sistemas (internos ou externos), decidir a estratégia de resposta, selecionar o provider/modelo adequado e executar a chamada correspondente.

## Objetivo secundário

Devolver uma **resposta padronizada** para o sistema de origem, de forma previsível e consistente, independentemente de qual provider foi usado internamente para gerá-la.

## Objetivo operacional atual e evoluções opcionais

Apoiar casos de **inteligência operacional**:

- Análise textual local de relatórios, logs, documentos e evidências enviados por payload.
- Apoio à parte exploratória/manual do QA de projetos externos por plano assistido, sem executar ações.
- Contrato controlado para origem `finguard`/`finguard-local`, sem leitura direta do repositório FinGuard.
- Leitura somente-leitura de artefatos Markdown/documentação via Artifact Reader apenas quando explicitamente habilitado, allowlisted e nunca para FinGuard.

O que permanece opcional/futuro: cliente HTTP no repositório FinGuard, QA visual real com provider multimodal, OCR/Playwright reais em ambiente configurado por humano, provider orchestration avançada e logs persistentes.

## Objetivos fora do escopo atual

- Calcular números financeiros oficiais de qualquer sistema externo (isso permanece exclusivamente no sistema de origem, ex.: FinGuard).
- Alterar, rodar migrations, seed/reset, testes ou comandos dentro de qualquer projeto externo, incluindo o FinGuard.
- Substituir o QA Automation do FinGuard (validação de API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E) — esse subsistema permanece interno ao FinGuard.
- Redesenhar frontend, layout ou identidade visual durante a reformulação documental/arquitetural em curso.
- Implementar o cliente HTTP real dentro do FinGuard nesta frente; isso é trabalho separado, no repositório FinGuard, com aprovação própria.

## Histórico do objetivo original (V1)

A V1 tinha como foco validar interface de conversa, estrutura de backend, fluxo de envio/recebimento e organização de código, como base para evoluir para uma API de IA. Esse objetivo inicial foi cumprido e superado: o projeto evoluiu de "chat pessoal de testes" para "orquestrador central de IA", conforme descrito acima.

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_PEDROCORE_IA]]
