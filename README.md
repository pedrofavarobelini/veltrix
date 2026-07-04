# PedroCore IA

Versão atual de produto: V5.1.9
Frente atual: PEDROCORE-REPLAN-01E — Fechamento documental da reformulação

## Estado atual da reformulação

- `01A` a `01D` concluídas e commitadas: visão oficial, contratos técnicos, arquitetura-alvo e planejamento de QA Intelligence.
- `01E` em fechamento: consolidação documental de toda a frente `PEDROCORE-REPLAN-01` (ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`).
- Documentação de contratos, arquitetura-alvo e QA Intelligence já criada (`docs/10-contratos/`, `docs/11-arquitetura-alvo/`, `docs/12-qa-intelligence/`).
- **Implementação ainda não iniciada** — nenhum código de Task Router, Prompt Builder, Project Context, Artifact Reader, QA Intelligence ou Audit/logs existe hoje.
- Frontend e design preservados sem alteração durante toda a reformulação.
- FinGuard não foi alterado, lido ou acessado em nenhuma etapa.

## O que é o PedroCore IA

O PedroCore IA é o **orquestrador central de IA do ecossistema de projetos Pedro**. Sistemas externos enviam mensagem, contexto e tipo de tarefa; o PedroCore interpreta a solicitação, escolhe uma estratégia de resposta, seleciona o provider/modelo adequado, monta o prompt correspondente e devolve uma resposta padronizada ao sistema de origem.

## O que ele faz hoje

- Expõe uma API própria (FastAPI) com chat multi-provider e listagem de providers, consumida hoje pelo seu próprio frontend React/Vite/TypeScript.
- Interpreta modo de resposta e monta o prompt correspondente para o provider selecionado.
- Aplica fallback automático para o `MockProvider` quando um provider real falha ou não está configurado.

## Planejado / futuro

- Receber chamadas de sistemas externos do ecossistema Pedro (não implementado hoje).
- Task Router, Prompt Builder e Project Context para classificar tarefa e montar contexto por sistema de origem.
- Resposta estruturada por tipo de tarefa, além do texto livre atual.
- Leitura somente-leitura de artefatos Markdown de projetos externos (ex.: relatórios de QA do FinGuard) como parte de inteligência operacional/QA Intelligence.
- Auditoria/logs de chamadas e persistência de histórico no backend.

## Relação com o FinGuard

O FinGuard é um projeto externo e independente. O PedroCore não altera código, dados, migrations, seeds, testes ou configuração do FinGuard, não executa comandos nele e não faz commit nele. Qualquer consumo futuro de artefatos do FinGuard (relatórios de QA em Markdown, documentação Obsidian) será sempre em modo somente leitura, e ainda não está implementado.

## Providers

| Provider | Situação |
|---|---|
| Mock | Real e funcional, sem custo, usado como fallback padrão |
| Gemini | Implementado; chave configurada localmente para testes |
| OpenAI | Implementado estruturalmente; sem chave configurada |
| Claude | Implementado estruturalmente; sem chave configurada |
| DeepSeek | Implementado estruturalmente; sem chave configurada |
| Grok/xAI | Implementado estruturalmente; sem chave configurada |

Qualquer provider real sem chave configurada cai automaticamente para o `MockProvider` (fallback obrigatório).

## Documentação oficial

- `README.md` (este arquivo)
- `VERSION.md`
- `docs/00-visao-geral/README.md`
- `docs/00-visao-geral/OBJETIVO.md`
- `docs/03-versoes/ROADMAP.md`
- `docs/09_STATUS_ATUAL.md`
- `docs/07-decisoes/DECISOES_TECNICAS.md`
- `docs/08_CHANGELOG.md`

Existem documentos antigos e duplicados em `docs/` ainda não consolidados/removidos, a serem tratados em etapa futura da reformulação documental.

## Segurança

O `.env` real não deve ser versionado. Apenas `apps/api/.env.example` pode ir para o Git.
