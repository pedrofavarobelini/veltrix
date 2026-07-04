# PedroCore IA — Visão Geral (Oficial)

> Este documento é a referência oficial de visão do projeto. Em caso de conflito com outros documentos de `docs/` (incluindo versões antigas ainda não consolidadas), esta versão prevalece.

## O que é o PedroCore IA

O PedroCore IA é o **provedor/orquestrador central de IA do ecossistema de projetos Pedro**. Sistemas externos enviam mensagem, contexto e tipo de tarefa; o PedroCore interpreta a solicitação, escolhe uma estratégia de resposta, seleciona o provider/modelo adequado, monta o prompt correspondente e devolve uma resposta padronizada ao sistema de origem.

## Para que serve

- Centralizar o acesso a múltiplos providers de IA (Gemini, OpenAI, Claude, DeepSeek, Grok/xAI) atrás de uma única API interna.
- Padronizar como qualquer sistema do ecossistema Pedro consome IA, em vez de cada projeto implementar sua própria integração com provedores.
- Servir de base futura para casos de **inteligência operacional**: análise de relatórios, logs, documentos e evidências de outros sistemas — incluindo, no futuro, apoio à parte exploratória/visual de QA do FinGuard.

## O que o PedroCore IA não é

- Não é (mais) apenas um chat pessoal de testes — esse era o escopo da V1, hoje superado pela visão de orquestrador central.
- Não é um modelo de IA próprio — não treina nem substitui os provedores de mercado (Decisão Técnica 001).
- Não é parte do FinGuard e não deve virar módulo interno dele.
- Não é, hoje, uma integração já implementada com sistemas externos — isso é objetivo futuro.

## Relação com sistemas externos

A visão-alvo é que sistemas externos do ecossistema Pedro consumam IA **preferencialmente através do PedroCore** (ver Decisão Técnica 008), em vez de chamarem provedores diretamente. Essa integração ainda não está implementada; hoje o PedroCore expõe apenas a API de chat/providers usada pelo seu próprio frontend.

## Relação futura com QA

O QA Automation nasceu dentro do FinGuard como subsistema independente de validação (API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E, relatórios e evidências) e permanece lá. Apenas a parte de IA exploratória/visual/inteligente do QA foi delegada como **caso de uso futuro** do PedroCore IA — não implementada nesta fase.

Os relatórios de QA do FinGuard hoje são Markdown livre, não JSON estruturado. Qualquer leitura futura desses relatórios pelo PedroCore deve ser planejada como leitura de texto/Markdown tolerante a variações, não como integração automática rígida.

## Limites com o FinGuard

- O FinGuard é um projeto externo e independente.
- O PedroCore não altera, não roda migrations, não executa seed/reset, não roda testes e não faz commit no FinGuard.
- O PedroCore não calcula números financeiros oficiais do FinGuard; pode, no futuro, explicar, resumir e sugerir a partir de artefatos lidos, mas os cálculos oficiais continuam exclusivamente no FinGuard.
- Qualquer consumo futuro de artefatos do FinGuard (relatórios de QA, documentação Obsidian) será sempre em modo **somente leitura**.

## Três contextos de IA (desambiguação)

O ecossistema Pedro tem hoje três contextos de IA distintos, que não devem ser confundidos:

1. **Assistente local do FinGuard** — feature já existente no backend do FinGuard (mock/Gemini/OpenAI), interna ao produto FinGuard. Não é a direção estratégica principal de IA do ecossistema.
2. **Agente exploratório de QA delegado ao PedroCore** — caso de uso futuro, ainda não implementado, referente à parte de IA visual/exploratória do QA Automation do FinGuard.
3. **PedroCore IA como camada central** — este projeto: orquestrador externo, multi-provider, pensado para ser a via preferencial de IA estratégica e de análise operacional de todo o ecossistema.

## Regra de frontend/design nesta fase

O frontend React/Vite/TypeScript e o design visual aprovado (V5.1.9) ficam **congelados** durante a reformulação documental e arquitetural em curso (`PEDROCORE-REPLAN-01`). Nenhuma mudança de layout, tema, identidade visual ou componente é feita nesta etapa.

## Local do repositório

```txt
C:\Projetos\pedrocore-ia
```
