# PedroCore IA

Versão atual de produto: V5.1.9
Tag técnica atual: `v6.0.0` — tag anotada criada em `ee2ac68` com a mensagem `v6.0.0 - MVP backend PedroCore IA`.
Frente técnica fechada: PEDROCORE-FINALIZE-04 — consolidação documental pós-MVP backend. A tag `v6.0.0` representa o fechamento do MVP backend, não o projeto completo.

## Estado atual

- Reformulação documental `PEDROCORE-REPLAN-01` (01A a 01E) concluída: visão oficial, contratos técnicos, arquitetura-alvo, QA Intelligence e fechamento (ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`).
- Backend com Task Router, Project Context (policy de `allowed_tasks`), Prompt Builder, Audit não persistente, Artifacts com limites duros (10 artefatos / 20k chars cada / 100k total) e **QA Text Analyzer local determinístico** (`qa_analysis`).
- Tarefas de QA crítica recebem `qa_skeleton` **preenchido por análise textual local** (`analysis_source="local_text_heuristic"`): detecção de sucesso/falha/erro/warning, risco (`low`→`critical`), `confidence`, `can_advance` conservador e sugestões seguras — sem IA externa, sem ler arquivos, sem executar comandos.
- **Release gate conservador**: `release_gate_review` só libera avanço com evidência textual limpa via análise local; mock/fallback/safe-mode/risco alto sempre bloqueiam, com `blocked_reason` e `RELEASE_GATE_BLOCKED`.
- **`POST /api/orchestrate`** existe: API operacional para sistemas externos (warnings com severidade, `warning_codes`, `error_code`, `blocked_reason`, `qa`, `release_gate`, `audit` completo), com autenticação interna opcional (`PEDROCORE_INTERNAL_API_KEY` + header `X-PedroCore-Api-Key`).
- **Safe mode**: `allow_real_provider=false` por padrão — Gemini/OpenAI/Claude/DeepSeek/Grok nunca são chamados sem autorização explícita (`PROVIDER_REAL_BLOCKED` + fallback Mock).
- Artefatos com campos de caminho (`path`, `file_path`, `absolute_path`, etc.) são **rejeitados sem leitura** (`ARTIFACT_PATH_REJECTED`).
- `POST /api/chat` permanece 100% compatível com requisições antigas e continua sem exigir API key.
- Frontend e design preservados sem alteração.
- Integração real com o FinGuard, leitura real de arquivos, execução de comandos, QA visual, log persistente, dashboard, Blocos 7–11 do planejamento maior, Bloco 12 e Blocos 13–15 finais ainda não existem.

## O que é o PedroCore IA

O PedroCore IA é o **orquestrador central de IA do ecossistema de projetos Pedro**. Sistemas externos enviam mensagem, contexto e tipo de tarefa; o PedroCore interpreta a solicitação, escolhe uma estratégia de resposta, seleciona o provider/modelo adequado, monta o prompt correspondente e devolve uma resposta padronizada ao sistema de origem.

## O que ele faz hoje

- Expõe uma API própria (FastAPI) com chat multi-provider (`/api/chat`), listagem de providers (`/api/providers`) e orquestração operacional (`/api/orchestrate`), consumida hoje pelo seu próprio frontend React/Vite/TypeScript.
- Interpreta modo de resposta e monta o prompt correspondente para o provider selecionado.
- Aplica fallback automático para o `MockProvider` quando um provider real falha, não está configurado ou é bloqueado pelo safe mode (`allow_real_provider=false` por padrão).
- Reconhece `task_type` e sinaliza criticidade/warnings de tarefa na resposta, com códigos padronizados (`warning_codes`) e severidade.
- Resolve um Project Context mínimo por `origin_system` (configuração interna, sem acesso a sistemas externos), avalia se a tarefa está na política do projeto (sem bloquear) e monta um `system_prompt` enriquecido via Prompt Builder antes de chamar o provider.
- Aceita artefatos textuais no payload (com limites de quantidade/tamanho e rejeição de campos de path) e os analisa localmente para tarefas de QA, por heurística determinística — sem IA externa.
- Decide release gate de forma conservadora (`can_advance`, `blocked_reason`), sem nunca aprovar com mock/fallback.
- Gera audit não persistente completo por requisição (`audit_id`, `timestamp`, `latency_ms`, `provider_used`, `safe_mode_blocked`, `risk_level`, `can_advance`).

## Planejado / futuro

- Receber chamadas de sistemas externos do ecossistema Pedro (não implementado hoje).
- QA Intelligence real (análise de fato dos artefatos recebidos) e Artifact Reader (leitura automática de arquivo).
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
