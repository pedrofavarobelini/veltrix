# PedroCore IA — Visão Geral (Oficial)

> Este documento é a referência oficial de visão do projeto. Em caso de conflito com outros documentos de `docs/` (incluindo versões antigas ainda não consolidadas), esta versão prevalece junto com [[../00_MAPEAMENTO_GERAL_PEDROCORE]].

## O que é o PedroCore IA

O PedroCore IA é o **provedor/orquestrador central de IA do ecossistema de projetos Pedro**. Sistemas externos enviam mensagem, contexto e tipo de tarefa; o PedroCore interpreta a solicitação, escolhe uma estratégia de resposta, seleciona o provider/modelo adequado, monta o prompt correspondente e devolve uma resposta padronizada ao sistema de origem.

## Para que serve

- Centralizar o acesso a múltiplos providers de IA (Gemini, OpenAI, Claude, DeepSeek, Grok/xAI) atrás de uma única API interna.
- Padronizar como qualquer sistema do ecossistema Pedro consome IA, em vez de cada projeto implementar sua própria integração com provedores.
- Servir de base para casos de **inteligência operacional**: análise textual local de relatórios, logs, documentos e evidências enviados por payload, com recursos reais (OCR/Playwright/multimodal) sempre opt-in.

## O que o PedroCore IA não é

- Não é (mais) apenas um chat pessoal de testes — esse era o escopo da V1, hoje superado pela visão de orquestrador central.
- Não é um modelo de IA próprio — não treina nem substitui os provedores de mercado (Decisão Técnica 001).
- Não é parte do FinGuard e não deve virar módulo interno dele.
- Não é um cliente embutido dentro de sistemas externos: do lado PedroCore há contrato controlado para `finguard`/`finguard-local`, mas o cliente HTTP dentro do FinGuard é frente separada.

## Relação com sistemas externos

A visão-alvo é que sistemas externos do ecossistema Pedro consumam IA **preferencialmente através do PedroCore** (ver Decisão Técnica 008), em vez de chamarem provedores diretamente. Hoje o PedroCore já expõe `/api/orchestrate` para consumo controlado; a integração cliente em cada sistema externo continua sendo frente separada.

## Relação futura com QA

O QA Automation nasceu dentro do FinGuard como subsistema independente de validação (API, backend, frontend, rotas, banco de teste, Prisma, Playwright, smoke tests, E2E, relatórios e evidências) e permanece lá. Do lado PedroCore, existem QA textual local, release gate conservador e exploração assistida/manual; QA visual real com provider multimodal permanece bloqueada/opt-in e não executa envio real nesta versão.

Os relatórios de QA do FinGuard hoje são Markdown livre, não JSON estruturado. Qualquer leitura futura desses relatórios pelo PedroCore deve ser planejada como leitura de texto/Markdown tolerante a variações, não como integração automática rígida.

## Limites com o FinGuard

- O FinGuard é um projeto externo e independente.
- O PedroCore não altera, não roda migrations, não executa seed/reset, não roda testes e não faz commit no FinGuard.
- O PedroCore não calcula números financeiros oficiais do FinGuard; pode, no futuro, explicar, resumir e sugerir a partir de artefatos lidos, mas os cálculos oficiais continuam exclusivamente no FinGuard.
- Qualquer consumo de artefatos do FinGuard deve ocorrer por payload textual controlado. O PedroCore não lê paths reais do FinGuard e o Artifact Reader é bloqueado para origem/caminho FinGuard.

## Três contextos de IA (desambiguação)

O ecossistema Pedro tem hoje três contextos de IA distintos, que não devem ser confundidos:

1. **Assistente local do FinGuard** — feature já existente no backend do FinGuard (mock/Gemini/OpenAI), interna ao produto FinGuard. Não é a direção estratégica principal de IA do ecossistema.
2. **Agente exploratório de QA delegado ao PedroCore** — no lado PedroCore existe como plano/manual assistido (`exploration`), sem execução autônoma; QA visual real continua não executada.
3. **PedroCore IA como camada central** — este projeto: orquestrador externo, multi-provider, pensado para ser a via preferencial de IA estratégica e de análise operacional de todo o ecossistema.

## Regra de frontend/design nesta fase

O frontend React/Vite/TypeScript e o design visual aprovado (V5.1.9) ficam **congelados** durante a reformulação documental e arquitetural em curso (`PEDROCORE-REPLAN-01`). Nenhuma mudança de layout, tema, identidade visual ou componente é feita nesta etapa.

## Local do repositório

```txt
C:\Projetos\pedrocore-ia
```
