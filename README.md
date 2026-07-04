# PedroCore IA

Versão atual de produto: V5.1.9
Frente atual: PEDROCORE-IMPLEMENT-01A/01B — Task Router mínimo + metadados de resposta

## Estado atual

- Reformulação documental `PEDROCORE-REPLAN-01` (01A a 01E) concluída: visão oficial, contratos técnicos, arquitetura-alvo, QA Intelligence e fechamento (ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`).
- Implementação inicial de código começou: Task Router mínimo existe no backend, reconhecendo `task_type` e sinalizando criticidade/warnings, sem bloqueio duro ainda.
- `POST /api/chat` permanece compatível com requisições antigas; nenhum endpoint novo de orquestração foi criado.
- Frontend e design preservados sem alteração.
- Integração real com o FinGuard ainda não existe.

## O que é o PedroCore IA

O PedroCore IA é o **orquestrador central de IA do ecossistema de projetos Pedro**. Sistemas externos enviam mensagem, contexto e tipo de tarefa; o PedroCore interpreta a solicitação, escolhe uma estratégia de resposta, seleciona o provider/modelo adequado, monta o prompt correspondente e devolve uma resposta padronizada ao sistema de origem.

## O que ele faz hoje

- Expõe uma API própria (FastAPI) com chat multi-provider e listagem de providers, consumida hoje pelo seu próprio frontend React/Vite/TypeScript.
- Interpreta modo de resposta e monta o prompt correspondente para o provider selecionado.
- Aplica fallback automático para o `MockProvider` quando um provider real falha ou não está configurado.
- Reconhece `task_type` (mínimo) e sinaliza criticidade/warnings de tarefa na resposta, sem alterar o comportamento do provider ainda.

## Planejado / futuro

- Receber chamadas de sistemas externos do ecossistema Pedro (não implementado hoje).
- Prompt Builder e Project Context reais, para montar prompt/contexto por sistema de origem a partir do `task_type`.
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
