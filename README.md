# PedroCore IA

Versão atual de produto: V5.1.9
Tags técnicas: `v6.0.0` (MVP backend, em `ee2ac68`) e `v7.0.0` (core operacional seguro finalizado localmente).
Status: **finalizado localmente** — `PEDROCORE-IMPLEMENT-05` (integrações reais controladas) e `PEDROCORE-FINALIZE-06` (enforcement final + fechamento) concluídas. Ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_FINAL.md`.
Frente pós-fechamento: `PEDROCORE-MODEL-FOUNDATION-01` — fundação de inteligência própria (Intelligence Layer, Report Intelligence, contrato de Local Model Provider e Evaluation Foundation). Ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01.md`.
Frente commitada mais recente: `PEDROCORE-QA-SAFETY-HARDENING-01` (`d6106b7`) — endurecimento de QA/safety sem reabrir o core funcional. Pytest `341 passed, 6 skipped, 2 warnings`; eval harness `14/14 passed`, `risk_level="none"`. Ver `docs/16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01.md`.
Frente documental anterior concluída: `PEDROCORE-DOCS-GRAPH-LINKING-01` — organização de links Markdown/Obsidian, sem alteração de código.
Frente **validada com sucesso** em 2026-07-09: `FINGUARD-PEDROCORE-ASSISTANT-REAL-PROVIDER-QA-01` - `provider=auto|gemini` controlado em `/api/orchestrate`, Gemini real somente com `allow_real_provider=true` e `GEMINI_API_KEY` no ambiente PedroCore; testes padrao usam stub/mock e o teste real fica opt-in. Corrigido bug de fallback que vazava texto tecnico/debug na resposta conversacional (ver `docs/08_CHANGELOG.md`); validacao manual confirmou resposta real via Gemini (`provider_used=gemini`, sem fallback). Pytest `351 passed, 7 skipped, 2 warnings`.
Frente atual concluída em 2026-07-18: observabilidade visual técnica local/QA com ring buffer sanitizado, provider/fallback/timeline, memória, avaliação e release gate em `#/observability`; integração real local FinGuard → PedroCore → FinGuard e replay conjunto aprovados. Pytest `368 passed, 7 skipped, 2 warnings`; Gemini real não foi executado nesta frente porque os dois opt-ins estavam desligados. Ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_OBSERVABILIDADE_LOCAL_01.md`.
Mapa atual completo: `docs/00_MAPEAMENTO_GERAL_PEDROCORE.md`.
Entrada Obsidian: `docs/MOC_PEDROCORE_IA.md`.

## Estado atual

- Reformulação documental `PEDROCORE-REPLAN-01` (01A a 01E) concluída: visão oficial, contratos técnicos, arquitetura-alvo, QA Intelligence e fechamento (ver `docs/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`).
- Backend com Task Router, Project Context (policy de `allowed_tasks`), Prompt Builder, Audit não persistente, Artifacts com limites duros (10 artefatos / 20k chars cada / 100k total) e **QA Text Analyzer local determinístico** (`qa_analysis`).
- Tarefas de QA crítica recebem `qa_skeleton` **preenchido por análise textual local** (`analysis_source="local_text_heuristic"`): detecção de sucesso/falha/erro/warning, risco (`low`→`critical`), `confidence`, `can_advance` conservador e sugestões seguras — sem IA externa, sem ler arquivos, sem executar comandos.
- **Release gate conservador**: `release_gate_review` só libera avanço com evidência textual limpa via análise local; mock/fallback/safe-mode/risco alto sempre bloqueiam, com `blocked_reason` e `RELEASE_GATE_BLOCKED`.
- **`POST /api/orchestrate`** existe: API operacional para sistemas externos (warnings com severidade, `warning_codes`, `error_code`, `blocked_reason`, `qa`, `release_gate`, `audit` completo), com autenticação interna opcional (`PEDROCORE_INTERNAL_API_KEY` + header `X-PedroCore-Api-Key`).
- **Safe mode**: `allow_real_provider=false` por padrão — Gemini/OpenAI/Claude/DeepSeek/Grok nunca são chamados sem autorização explícita (`PROVIDER_REAL_BLOCKED` + fallback Mock).
- Artefatos com campos de caminho (`path`, `file_path`, `absolute_path`, etc.) são **rejeitados sem leitura** (`ARTIFACT_PATH_REJECTED`) — exceto quando o **Artifact Reader controlado** (Bloco 9) está explicitamente habilitado (`PEDROCORE_ARTIFACT_READER_ENABLED=true`, desabilitado por padrão) e o caminho está dentro da allowlist; nunca para origem FinGuard, nunca `.env`, nunca binário, nunca segredo, nunca path traversal.
- **Contrato FinGuard → PedroCore** (Bloco 8) definido por payload fake: `origin_system` `finguard`/`finguard-local` read-only, sem qualquer acesso ao repositório real (ver `docs/11-integracoes/CONTRATO_FINGUARD_PEDROCORE.md`).
- **QA visual stub** (Bloco 10): artefatos visuais geram `visual_qa_analysis` conservador exigindo revisão humana — sem OCR, sem provider multimodal, sem Playwright; release gate nunca avança só com evidência visual.
- **Agente exploratório assistido** (Bloco 11): tasks exploratórias geram plano/checklist manual (`exploration`) com `can_execute_actions=false` sempre — nada é executado automaticamente.
- **Fundação de inteligência própria** (`PEDROCORE-MODEL-FOUNDATION-01`): Intelligence Layer determinística (`intelligence_layer/`, plano interno por task com `allow_real_provider` sempre `false`), Report Intelligence Foundation (`report_intelligence/`, sinais determinísticos de relatórios técnicos por payload, sem persistência — **relatórios não treinam IA**), contrato futuro do provider generativo local (`providers/local_model_contract.py`, `local_model` ≠ `local_qa`, sem backend instalado) e Evaluation Foundation (`evaluation/`, checks de segurança/coerência). O PedroCore **não** é um modelo treinado e não substitui providers externos; não há fine-tuning, autoaprendizado nem modelo local rodando.
- **Inteligência de ecossistema** (`PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01`): contrato consolidado para sistemas consumidores (`docs/10-contratos/CONTRATO_ECOSYSTEM_ASSISTANT.md`, tasks `assistant_chat`/`finance_advice` com disclaimer obrigatório/`project_status`/`report_memory_query`); memória técnica controlada default-off (`report_memory/`, `POST /api/reports/analyze|ingest`, `GET /api/project-memory/{id}/summary`, `context_from_memory` opt-in — **relatórios não treinam IA**); provider generativo local `local_model` opt-in default-off (fake transport em teste, **nenhuma rede nesta frente**, nunca aprova release gate); eval harness determinístico (`eval_harness/`, 11 fixtures, sem provider real). O Prompt Builder agora recebe as instruções do `IntelligencePlan` (`[Plano de inteligência]`).
- **QA Safety Hardening** (`PEDROCORE-QA-SAFETY-HARDENING-01`): guard estrutural contra provider real em testes, Report Memory safety, policy negativa, contrato `/api/orchestrate` e eval harness estendido. Provider real e rede real nao foram chamados em testes; Report Memory segue default-off e nao e treinamento; `local_model` real, FinGuard e `qa:finalize:02` ficaram fora de escopo.
- **Observabilidade local/QA**: store volátil sanitizado, limitado e default-off; endpoints `/api/observability/*`; painel `#/observability`; provider solicitado/efetivo, tentativas, fallback, timeline, QA, memória, avaliação, release gate e audit ID visíveis apenas no PedroCore. Memória técnica não altera pesos e treinamento de modelo não foi implementado.
- `POST /api/chat` permanece 100% compatível com requisições antigas e continua sem exigir API key.
- Frontend e design preservados sem alteração.
- Cliente HTTP do Assistente no FinGuard e replay local integrado estão implementados. OCR real, QA visual real com provider multimodal, Playwright real, persistência da observabilidade e deploy/push ainda são opcionais e exigem aprovação própria. Bloco 12 (dashboard público/admin) permanece cancelado por decisão de produto.

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

## Opcional / futuro

- Cliente HTTP no repositório do FinGuard consumindo `POST /api/orchestrate` (frente separada, com aprovação própria).
- Push para GitHub/portfólio e deploy.
- Execução real de OCR, Playwright ou multimodal somente com flags, dependências/chaves reais e revisão humana.
- Provider orchestration avançada por custo/qualidade/task.
- Log persistente/histórico backend se a decisão de produto mudar; dashboard/logs/admin (Bloco 12) segue cancelado.

## Relação com o FinGuard

O FinGuard é um projeto externo e independente. Do lado PedroCore, o contrato controlado já reconhece `origin_system=finguard` e `origin_system=finguard-local` em `POST /api/orchestrate`, com tasks permitidas, policy forte, Artifact Reader bloqueado para FinGuard e provider real bloqueado por padrão. O PedroCore não altera código, dados, migrations, seeds, testes ou configuração do FinGuard, não executa comandos nele, não lê path real do repositório e não faz commit nele.

Para o Assistente IA do FinGuard, o consumidor pode pedir `provider=mock|auto|gemini`, mas o PedroCore decide o provider final. Gemini real exige `allow_real_provider=true` e `GEMINI_API_KEY` somente no ambiente PedroCore; o FinGuard nao recebe nem repassa essa chave.

## Providers

| Provider | Situação |
|---|---|
| local_qa | Pseudo-provider deterministico local para QA/release gate; sem provider externo |
| Auto | Politica controlada para consumidor externo; nesta frente escolhe Gemini somente com autorizacao e chave configurada |
| Mock | Real e funcional, sem custo, usado como fallback padrão |
| Gemini | Implementado estruturalmente; chamada real exige chave/configuração e `allow_real_provider=true` |
| OpenAI | Implementado estruturalmente; chamada real exige chave/configuração e `allow_real_provider=true` |
| Claude | Implementado estruturalmente; chamada real exige chave/configuração e `allow_real_provider=true` |
| DeepSeek | Implementado estruturalmente; chamada real exige chave/configuração e `allow_real_provider=true` |
| Grok/xAI | Implementado estruturalmente; chamada real exige chave/configuração e `allow_real_provider=true` |

Qualquer provider real sem autorização explícita cai para bloqueio de safe mode (`PROVIDER_REAL_BLOCKED`) e fallback Mock. Provider real nunca aprova release gate sozinho.

## Documentação oficial

- `README.md` (este arquivo)
- `VERSION.md`
- `docs/00_MAPEAMENTO_GERAL_PEDROCORE.md`
- `docs/MOC_PEDROCORE_IA.md`
- `docs/MOC_QA_SAFETY_HARDENING.md`
- `docs/MOC_ESTUDO_PEDROCORE.md`
- `docs/00-visao-geral/README.md`
- `docs/00-visao-geral/OBJETIVO.md`
- `docs/03-versoes/ROADMAP.md`
- `docs/09_STATUS_ATUAL.md`
- `docs/07-decisoes/DECISOES_TECNICAS.md`
- `docs/08_CHANGELOG.md`

Existem documentos antigos e duplicados em `docs/` ainda não consolidados/removidos, a serem tratados em etapa futura da reformulação documental.

## Segurança

O `.env` real não deve ser versionado. Apenas `apps/api/.env.example` pode ir para o Git.
