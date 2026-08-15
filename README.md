# PedroCore IA

## MICROFRENTE ATUAL — STRUCTA CONSUMER

`PEDROCORE-STRUCTA-CONSUMER-01` registrou o Structa como consumer oficial de
menor privilégio: `project_id=structa`, identidade `registered`, papel
`technical_tool`, somente `qa_report_analysis` e somente Gemini em ambiente
não produtivo. Provider real e fallback real continuam default-off. A frente
foi inteiramente offline (`plannedRealCalls=0`, `actualRealCalls=0`) e está em
`PedroCore IA/17-multi-provider-safe-evolution/PEDROCORE_STRUCTA_CONSUMER_01.md`.

## ENCERRAMENTO DO CORE — PRESERVADO

```text
PEDROCORE ENCERRADO — CORE OPERACIONAL CONCLUÍDO
```

Frente: `FINGUARD-PEDROCORE-CANONICAL-REPLAY-DOCS-GRAPH-FINALIZE-01`.
Documento: `PedroCore IA/19-encerramento-final/PEDROCORE_ENCERRAMENTO_FINAL_01.md`.

- Assistente IA do FinGuard: **homologação real 4/4**. O cenário `Organizar`, última limitação aberta, foi aprovado com Gemini real (`provider_effective=gemini`, `fallback=false`, `retry=0`, um único dispatch).
- Validação integral desta frente: **`736 passed, 7 skipped, 2 warnings`**; eval harness `14/14`, `risk_level="none"`, sem chamadas externas reais na suíte.
- Grafo documental Obsidian: **íntegro** — 128 documentos, 697 links resolvidos, zero órfãos, zero links quebrados. Validado por `app.modules.docs_graph`, não por `.obsidian/graph.json`.
- Arquitetura multi-provider concluída; operação multi-provider **automática** permanece indisponível porque só `gemini + gemini-3.5-flash` está homologado e elegível. Isso é decisão de homologação, não pendência.
- Cancelamento remoto continua **não comprovável** — limitação aceita e documentada.
- Nenhuma implementação obrigatória restante.

Checkpoint anterior (**histórico**): `PEDROCORE-MULTI-PROVIDER-DOCS-CONSOLIDATION-01` consolidou as Etapas 1–7 da evolução multi-provider segura; naquele momento a suíte era `570 passed, 7 skipped`. Ver `PedroCore IA/17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7.md` e `PedroCore IA/MOC_MULTI_PROVIDER_SAFE_EVOLUTION.md`.

### Validar o grafo documental

```powershell
cd apps\api
.venv\Scripts\python.exe -m app.modules.docs_graph.service
```

Sai com código diferente de zero diante de órfão, beco sem saída, link quebrado, link ambíguo, basename duplicado ou documento inalcançável a partir do MOC raiz.

Versão atual de produto: V5.1.9
Tags técnicas: `v6.0.0` (MVP backend, em `ee2ac68`) e `v7.0.0` (core operacional seguro finalizado localmente).
Status: **finalizado localmente** — `PEDROCORE-IMPLEMENT-05` (integrações reais controladas) e `PEDROCORE-FINALIZE-06` (enforcement final + fechamento) concluídas. Ver `PedroCore IA/13-fechamento/FECHAMENTO_PEDROCORE_FINAL.md`.
Frente pós-fechamento: `PEDROCORE-MODEL-FOUNDATION-01` — fundação de inteligência própria (Intelligence Layer, Report Intelligence, contrato de Local Model Provider e Evaluation Foundation). Ver `PedroCore IA/13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01.md`.
Checkpoint histórico: `PEDROCORE-QA-SAFETY-HARDENING-01` (`d6106b7`) — endurecimento de QA/safety sem reabrir o core funcional. Naquele checkpoint: Pytest `341 passed, 6 skipped, 2 warnings`; eval harness `14/14 passed`, `risk_level="none"`. Ver `PedroCore IA/16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01.md`.
Frente documental anterior concluída: `PEDROCORE-DOCS-GRAPH-LINKING-01` — organização de links Markdown/Obsidian, sem alteração de código.
Frente **validada com sucesso** em 2026-07-09: `FINGUARD-PEDROCORE-ASSISTANT-REAL-PROVIDER-QA-01` - `provider=auto|gemini` controlado em `/api/orchestrate`, Gemini real somente com `allow_real_provider=true` e `GEMINI_API_KEY` no ambiente PedroCore; testes padrao usam stub/mock e o teste real fica opt-in. Corrigido bug de fallback que vazava texto tecnico/debug na resposta conversacional (ver `PedroCore IA/08_CHANGELOG.md`); validacao manual confirmou resposta real via Gemini (`provider_used=gemini`, sem fallback). Pytest `351 passed, 7 skipped, 2 warnings`.
Checkpoint histórico de 2026-07-18: observabilidade visual técnica local/QA com ring buffer sanitizado, provider/fallback/timeline, memória, avaliação e release gate em `#/observability`; integração real local FinGuard → PedroCore → FinGuard e replay conjunto aprovados. Naquele checkpoint: Pytest `368 passed, 7 skipped, 2 warnings`; Gemini real não foi executado porque os dois opt-ins estavam desligados. Ver `PedroCore IA/13-fechamento/FECHAMENTO_PEDROCORE_OBSERVABILIDADE_LOCAL_01.md`.
Mapa atual completo: `PedroCore IA/00_MAPEAMENTO_GERAL_PEDROCORE.md`.
Entrada Obsidian: `PedroCore IA/MOC_PEDROCORE_IA.md`.

## Vault documental canônico

Desde 2026-08-02, toda a documentação canônica está exclusivamente em
`PedroCore IA/`. A antiga árvore rastreada `docs/` foi reorganizada com
preservação comprovada de 127/127 documentos anteriores. A prova e os comandos
de validação estão em `PedroCore IA/MANIFESTO_REORGANIZACAO_20260802.md`.

## Estado atual

- Reformulação documental `PEDROCORE-REPLAN-01` (01A a 01E) concluída: visão oficial, contratos técnicos, arquitetura-alvo, QA Intelligence e fechamento (ver `PedroCore IA/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md`).
- Backend com Task Router, Project Context (policy de `allowed_tasks`), Prompt Builder, Audit não persistente, Artifacts com limites duros (10 artefatos / 20k chars cada / 100k total) e **QA Text Analyzer local determinístico** (`qa_analysis`).
- Tarefas de QA crítica recebem `qa_skeleton` **preenchido por análise textual local** (`analysis_source="local_text_heuristic"`): detecção de sucesso/falha/erro/warning, risco (`low`→`critical`), `confidence`, `can_advance` conservador e sugestões seguras — sem IA externa, sem ler arquivos, sem executar comandos.
- **Release gate conservador**: `release_gate_review` só libera avanço com evidência textual limpa via análise local; mock/fallback/safe-mode/risco alto sempre bloqueiam, com `blocked_reason` e `RELEASE_GATE_BLOCKED`.
- **`POST /api/orchestrate`** existe: API operacional para sistemas externos (warnings com severidade, `warning_codes`, `error_code`, `blocked_reason`, `qa`, `release_gate`, `audit` completo), com autenticação interna opcional (`PEDROCORE_INTERNAL_API_KEY` + header `X-PedroCore-Api-Key`).
- **Safe mode**: `allow_real_provider=false` por padrão — Gemini/OpenAI/Claude/DeepSeek/Grok nunca são chamados sem autorização explícita (`PROVIDER_REAL_BLOCKED` + fallback Mock).
- Artefatos com campos de caminho (`path`, `file_path`, `absolute_path`, etc.) são **rejeitados sem leitura** (`ARTIFACT_PATH_REJECTED`) — exceto quando o **Artifact Reader controlado** (Bloco 9) está explicitamente habilitado (`PEDROCORE_ARTIFACT_READER_ENABLED=true`, desabilitado por padrão) e o caminho está dentro da allowlist; nunca para origem FinGuard, nunca `.env`, nunca binário, nunca segredo, nunca path traversal.
- **Contrato FinGuard → PedroCore** (Bloco 8) definido por payload fake: `origin_system` `finguard`/`finguard-local` read-only, sem qualquer acesso ao repositório real (ver `PedroCore IA/11-integracoes/CONTRATO_FINGUARD_PEDROCORE.md`).
- **QA visual stub** (Bloco 10): artefatos visuais geram `visual_qa_analysis` conservador exigindo revisão humana — sem OCR, sem provider multimodal, sem Playwright; release gate nunca avança só com evidência visual.
- **Agente exploratório assistido** (Bloco 11): tasks exploratórias geram plano/checklist manual (`exploration`) com `can_execute_actions=false` sempre — nada é executado automaticamente.
- **Fundação de inteligência própria** (`PEDROCORE-MODEL-FOUNDATION-01`): Intelligence Layer determinística (`intelligence_layer/`, plano interno por task com `allow_real_provider` sempre `false`), Report Intelligence Foundation (`report_intelligence/`, sinais determinísticos de relatórios técnicos por payload, sem persistência — **relatórios não treinam IA**), contrato futuro do provider generativo local (`providers/local_model_contract.py`, `local_model` ≠ `local_qa`, sem backend instalado) e Evaluation Foundation (`evaluation/`, checks de segurança/coerência). O PedroCore **não** é um modelo treinado e não substitui providers externos; não há fine-tuning, autoaprendizado nem modelo local rodando.
- **Inteligência de ecossistema** (`PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01`): contrato consolidado para sistemas consumidores (`PedroCore IA/10-contratos/CONTRATO_ECOSYSTEM_ASSISTANT.md`, tasks `assistant_chat`/`finance_advice` com disclaimer obrigatório/`project_status`/`report_memory_query`); memória técnica controlada default-off (`report_memory/`, `POST /api/reports/analyze|ingest`, `GET /api/project-memory/{id}/summary`, `context_from_memory` opt-in — **relatórios não treinam IA**); provider generativo local `local_model` opt-in default-off (fake transport em teste, **nenhuma rede nesta frente**, nunca aprova release gate); eval harness determinístico (`eval_harness/`, 11 fixtures, sem provider real). O Prompt Builder agora recebe as instruções do `IntelligencePlan` (`[Plano de inteligência]`).
- **QA Safety Hardening** (`PEDROCORE-QA-SAFETY-HARDENING-01`): guard estrutural contra provider real em testes, Report Memory safety, policy negativa, contrato `/api/orchestrate` e eval harness estendido. Provider real e rede real nao foram chamados em testes; Report Memory segue default-off e nao e treinamento; `local_model` real, FinGuard e `qa:finalize:02` ficaram fora de escopo.
- **Observabilidade local/QA**: store volátil sanitizado, limitado e default-off; endpoints `/api/observability/*`; painel `#/observability`; provider solicitado/efetivo, tentativas, fallback, timeline, QA, memória, avaliação, release gate e audit ID visíveis apenas no PedroCore. Memória técnica não altera pesos e treinamento de modelo não foi implementado.
- **Evolução multi-provider segura (Etapas 1–7)**: catálogo explícito, identidade/autorização por projeto, binding total de provider/modelo, shadow routing, roteamento `enforced` determinístico, circuit breaker local/default-off e fallback real estritamente pre-dispatch/default-off. O motor está concluído; diversificação real continua bloqueada até a homologação de um segundo provider/modelo.
- **Consumer Structa**: `origin_system=Structa` resolve para `structa`; somente credencial registrada `technical_tool`, task `qa_report_analysis`, Gemini e ambiente não produtivo podem ser autorizados. Sem credencial, com role indevido, provider diferente ou origem desconhecida, o fluxo falha fechado antes de chamada real.
- `POST /api/chat` permanece 100% compatível com requisições antigas e continua sem exigir API key.
- Frontend e design preservados sem alteração.
- Cliente HTTP do Assistente no FinGuard e replay local integrado estão implementados. OCR real, QA visual real com provider multimodal, Playwright real, persistência da observabilidade e deploy/push ainda são opcionais e exigem aprovação própria. Bloco 12 (dashboard público/admin) permanece cancelado por decisão de produto.

## O que é o PedroCore IA

O PedroCore IA é o **orquestrador central de IA do ecossistema de projetos Pedro**. Sistemas externos enviam mensagem, contexto e tipo de tarefa; o PedroCore interpreta a solicitação, escolhe uma estratégia de resposta, seleciona o provider/modelo adequado, monta o prompt correspondente e devolve uma resposta padronizada ao sistema de origem.

## O que ele faz hoje

- Expõe uma API própria (FastAPI) com chat multi-provider (`/api/chat`), listagem de providers (`/api/providers`) e orquestração operacional (`/api/orchestrate`), consumida hoje pelo seu próprio frontend React/Vite/TypeScript.
- Interpreta modo de resposta e monta o prompt correspondente para o provider selecionado.
- Aplica fallback seguro para o `MockProvider` quando a execução real não pode prosseguir ou falha. O fallback entre providers reais é default-off, limitado a uma única tentativa secundária e somente ocorre após falha comprovadamente pre-dispatch; timeout é ambíguo e nunca dispara secundário.
- Reconhece `task_type` e sinaliza criticidade/warnings de tarefa na resposta, com códigos padronizados (`warning_codes`) e severidade.
- Resolve um Project Context mínimo por `origin_system` (configuração interna, sem acesso a sistemas externos), avalia se a tarefa está na política do projeto (sem bloquear) e monta um `system_prompt` enriquecido via Prompt Builder antes de chamar o provider.
- Aceita artefatos textuais no payload (com limites de quantidade/tamanho e rejeição de campos de path) e os analisa localmente para tarefas de QA, por heurística determinística — sem IA externa.
- Decide release gate de forma conservadora (`can_advance`, `blocked_reason`), sem nunca aprovar com mock/fallback.
- Gera audit não persistente completo por requisição (`audit_id`, `timestamp`, `latency_ms`, `provider_used`, `safe_mode_blocked`, `risk_level`, `can_advance`).

## Opcional / futuro

- Homologação controlada de um segundo provider/modelo real, escolhendo Claude ou OpenAI em frente separada.
- Push para GitHub/portfólio e deploy.
- Execução real de OCR, Playwright ou multimodal somente com flags, dependências/chaves reais e revisão humana.
- Provider orchestration avançada por custo/qualidade/task.
- Log persistente/histórico backend se a decisão de produto mudar; dashboard/logs/admin (Bloco 12) segue cancelado.

## Relação com o FinGuard

O FinGuard é um projeto externo e independente. Do lado PedroCore, o contrato controlado já reconhece `origin_system=finguard` e `origin_system=finguard-local` em `POST /api/orchestrate`, com tasks permitidas, policy forte, Artifact Reader bloqueado para FinGuard e provider real bloqueado por padrão. O PedroCore não altera código, dados, migrations, seeds, testes ou configuração do FinGuard, não executa comandos nele, não lê path real do repositório e não faz commit nele.

Para o Assistente IA do FinGuard, o contrato comum é pedir `provider=auto` sem escolher modelo; o PedroCore resolve identidade, autorização, provider e modelo. Execução real exige `allow_real_provider=true`, credencial própria registrada no PedroCore e binding elegível. O FinGuard não recebe nem repassa chaves. Neste checkpoint, somente Gemini está homologado e elegível.

## Relação com o Structa

O Structa é consumer externo independente e read-only. Seu onboarding não
reutiliza identidade ou permissões FinGuard/PedroCore, não acessa o repositório
Structa e não executa filesystem, Executor ou Planner. Uma chamada real
continua proibida até Gate próprio do Structa com autorização humana nova.

## Providers

| Provider | Situação |
|---|---|
| local_qa | Pseudo-provider deterministico local para QA/release gate; sem provider externo |
| Auto | Política determinística com shadow/enforced, health e fallback seguro; operacionalmente só pode escolher Gemini neste checkpoint |
| Mock | Real e funcional, sem custo, usado como fallback padrão |
| Gemini | `gemini-3.5-flash` homologado e autorizado para auto conforme identidade/policy |
| OpenAI | `gpt-5.2-mini` catalogado, não homologado e não autorizado para auto |
| Claude | `claude-sonnet-4-5` catalogado, não homologado e não autorizado para auto |
| DeepSeek | `deepseek-chat` catalogado, não homologado e não autorizado para auto |
| Grok/xAI | `grok-4.3` catalogado, não homologado e não autorizado para auto |

Qualquer provider real sem autorização explícita cai para bloqueio de safe mode (`PROVIDER_REAL_BLOCKED`) e fallback Mock. Provider real nunca aprova release gate sozinho.

## Documentação oficial

- `README.md` (este arquivo)
- `VERSION.md`
- `PedroCore IA/00_MAPEAMENTO_GERAL_PEDROCORE.md`
- `PedroCore IA/MOC_PEDROCORE_IA.md`
- `PedroCore IA/MOC_MULTI_PROVIDER_SAFE_EVOLUTION.md`
- `PedroCore IA/17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7.md`
- `PedroCore IA/MOC_QA_SAFETY_HARDENING.md`
- `PedroCore IA/MOC_ESTUDO_PEDROCORE.md`
- `PedroCore IA/00-visao-geral/README.md`
- `PedroCore IA/00-visao-geral/OBJETIVO.md`
- `PedroCore IA/03-versoes/ROADMAP.md`
- `PedroCore IA/09_STATUS_ATUAL.md`
- `PedroCore IA/07-decisoes/DECISOES_TECNICAS.md`
- `PedroCore IA/08_CHANGELOG.md`

Existem documentos históricos e duplicados em `PedroCore IA/` ainda não consolidados/removidos; eles foram preservados e continuam sendo uma melhoria opcional.

## Segurança

O `.env` real não deve ser versionado. Apenas `apps/api/.env.example` pode ir para o Git.
