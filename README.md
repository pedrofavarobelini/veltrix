# PedroCore IA

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Licenciado sob a **Apache License 2.0** (SPDX: `Apache-2.0`). Veja [LICENSE](LICENSE).

## FRENTE ATUAL — AI RUNTIME & LEARNING CONTROL PLANE

`PEDROCORE-CONTROL-PLANE-01` reorganizou o PedroCore em duas fronteiras
internas declaradas e verificadas por teste, e construiu sobre elas a
plataforma de integração universal.

```text
                     PEDROCORE (modular monolith)
                              │
        ┌─────────────────────┴─────────────────────┐
   RUNTIME PLANE                              LEARNING PLANE
   responder agora  ──── evidência/contratos ────►  aprender depois
```

**O que existe hoje**

- **Universal Contracts V1**, congelados: Project Capability Manifest, Quality
  Evidence (QEC), Execution Outcome, Learning Source e o envelope de
  integração. Alterar a forma de qualquer um quebra o build.
- **Evidence Platform**: ingestão fail-closed com validação de contrato,
  fronteira de autoridade, varredura de privacidade, fingerprint do servidor,
  idempotência e deduplicação.
- **Learning Governance**: seleção manual, elegibilidade, privacidade,
  proveniência, autorização e ciclo de vida de candidato.
- **Resiliência**: outbox **durável** com backoff, dead-letter e reconciliação.
  Sobrevive tanto ao PedroCore fora do ar quanto ao restart do próprio
  consumidor — um outbox que não sobrevive ao processo é um buffer, não um
  outbox.
- **Dataset Control Plane**: registry, versionamento, linhagem e split, com
  materialização travada por readiness real.
- **Evaluation & Training Foundation**: baseline, comparação, promoção e
  rollback — sem executar treinamento.

**Princípio que atravessa tudo**

O consumidor envia **fato observado**; o PedroCore emite **julgamento**. Um
payload que tenta declarar elegibilidade, autorização, score autoritativo ou
um Training Candidate pronto é recusado inteiro, em qualquer profundidade e
qualquer grafia.

```text
Operational Data  !=  Training Candidate  !=  Canonical Training Example
```

**Estado**

```text
CONTROL_PLANE_READY      governança completa e testada
DATASET_NOT_READY        correto — não há população real autorizada
```

`automatic_collection` é `Literal[False]`: um tipo que faz o validador recusar
`True`, não uma flag desligada.

**Validação:** `1340 passed, 21 skipped, 0 failed`; Ruff integral PASS; build
do frontend PASS; grafo documental íntegro; OpenAPI sem breaking change
(37 → 39 paths, todos aditivos).

Documentos: `PedroCore IA/20-control-plane/`.

## FRENTE ANTERIOR — ELYRA ONBOARDING V1 TEXTUAL

`PEDROCORE-ELYRA-ONBOARDING-V1-TEXTUAL` registrou Elyra como consumer oficial:
`project_id=elyra`, identidade `registered`, papel `common_consumer`, uma única
task `wellbeing_report_interpretation` e schemas strict/versionados. CI usa
mock determinístico; execução real é `provider=auto`, Gemini não produtivo,
sem modelo do caller e sem fallback. Resultado: **PASS**, `959 passed, 21
skipped`, Ruff integral, eval `14/14` e grafo `155/822`; zero chamadas
externas. Contrato:
`PedroCore IA/10-contratos/CONTRATO_ELYRA_TEXTUAL_V1.md`.

## MICROFRENTE ANTERIOR — STRUCTA CONSUMER

`PEDROCORE-STRUCTA-CONSUMER-01` registrou o Structa como consumer oficial de
menor privilégio: `project_id=structa`, identidade `registered`, papel
`technical_tool`, somente `qa_report_analysis` e somente Gemini em ambiente
não produtivo. Provider real e fallback real continuam default-off. A frente
foi inteiramente offline (`plannedRealCalls=0`, `actualRealCalls=0`) e está em
`PedroCore IA/17-multi-provider-safe-evolution/PEDROCORE_STRUCTA_CONSUMER_01.md`.

## ENCERRAMENTO DO CORE — PRESERVADO
## Estado consolidado — Eras 1 a 3

```text
ERA 1 — PASS                         Operational Intelligence Foundation
ERA 2 — PASS                         Motor de Risco de Execução por IA
ERA 3 — FOUNDATION PASS              Training Foundation
        TRAINING DEFERRED             DATASET_NOT_READY
```

Candidate Acquisition está implementada, mas há **zero candidatos reais
autorizados**. Não existem Canonical Dataset, splits, fine-tuning, modelo próprio
ou Local Provider treinado; Hugging Face não foi iniciado. Operational Learning
usa memória, evidências, outcomes, patterns, retrieval e policies sem alterar
pesos neurais.

Checkpoint documental e arquitetura completa:
[`PedroCore IA/19-encerramento-final/PEDROCORE_FECHAMENTO_DOCUMENTAL_FINAL_ERAS_1_A_3.md`](PedroCore%20IA/19-encerramento-final/PEDROCORE_FECHAMENTO_DOCUMENTAL_FINAL_ERAS_1_A_3.md).
Última evidência backend disponível: `924 passed, 7 skipped, 2 warnings`; Ruff
global PASS; Pyright Era 3 sem erros. Esta reconciliação não repetiu testes e não
alterou código, configuração ou Git.

Gateway e orquestrador central de IA para um ecossistema de projetos.

Em vez de cada aplicação integrar diretamente com Gemini, OpenAI, Claude e
outros — duplicando chaves, política de custo, fallback e tratamento de erro —
elas falam com o PedroCore. Ele resolve **identidade, autorização, provider,
modelo e prompt**, e devolve uma resposta padronizada.

```text
FinGuard  ─┐
Structa   ─┤
Projeto C ─┼──→  PedroCore IA  ──→  Providers (Gemini, …)
Projeto N ─┘         │
                     └── política · identidade · safe mode · fallback · audit
```

**Versão de produto:** V5.2.0 · **API:** 0.2.0 · **Status:** operacional para
uso local e para o ecossistema local.

> **Este repositório publica código, não uma API pronta para a internet.** A
> configuração padrão é voltada ao uso local. Ver [Segurança](#segurança).

---

## Arquitetura

**Backend** — FastAPI (Python), organizado em módulos por responsabilidade:

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
- **Consumer Elyra textual V1**: `origin_system=elyra`, credencial registrada
  `common_consumer`, task única `wellbeing_report_interpretation`, input/output
  strict e versionados, correlation e idempotência. Multimodal e learning
  permanecem negados; PedroCore não acessa banco/Storage Elyra nem recalcula
  métricas oficiais.
- `POST /api/chat` permanece 100% compatível com requisições antigas e continua sem exigir API key.
- Frontend e design preservados sem alteração.
- Cliente HTTP do Assistente no FinGuard e replay local integrado estão implementados. OCR real, QA visual real com provider multimodal, Playwright real, persistência da observabilidade e deploy/push ainda são opcionais e exigem aprovação própria. Bloco 12 (dashboard público/admin) permanece cancelado por decisão de produto.
| Camada | Papel |
| --- | --- |
| Task Router | Reconhece `task_type`, criticidade e estilo de resposta |
| Caller Identity | Identifica o projeto chamador; a origem no payload é só alegação |
| Project Context / Policy | Decide se a tarefa é permitida para aquele projeto |
| Provider Catalog / Binding | Valida provider **e** modelo como par, antes de qualquer adapter |
| Shadow / Enforced Routing | Política determinística de escolha de provider |
| Provider Health | Circuit breaker local, default-off |
| Prompt Builder | Monta o prompt enriquecido |
| Artifacts | Recebe artefatos textuais com limites duros |
| QA Analysis / Release Gate | Análise determinística local, sem IA externa |
| Audit / Observability | Rastro por requisição; volátil e default-off |

**Frontend** — React + Vite + TypeScript. Chat com histórico local, seletor de
IA, Configurações em drawer, ditado por voz e anexos textuais.

---

## Relação com a Elyra

A Elyra é consumer externo independente e read-only. Envia somente o snapshot
determinístico preparado por ela para interpretação não clínica. O PedroCore
não acessa banco, Storage, diário integral ou mídia da Elyra. A Stage 09 usa
somente a capability textual V1; multimodal Stage 12 e dataset/learning Stage
13 continuam fora do contrato e falham fechados.

## Providers

| Provider | Situação |
| --- | --- |
| **Gemini** | `gemini-3.5-flash` — **homologado** e autorizado para `auto` |
| OpenAI | `gpt-5.2-mini` — catalogado, **não homologado** |
| Claude | `claude-sonnet-4-5` — catalogado, **não homologado** |
| DeepSeek | `deepseek-chat` — catalogado, **não homologado** |
| Grok/xAI | `grok-4.3` — catalogado, **não homologado** |
| `mock` | Interno. Fallback seguro, sem custo, sem rede |
| `local_qa` | Interno. Analisador determinístico para release gate |
| `local_model` | Interno. Provider generativo local opt-in, sem transport real |
| `auto` | Estratégia de roteamento, **não é uma IA** |

Um provider real sem autorização explícita nunca é chamado: vira
`PROVIDER_REAL_BLOCKED` e fallback Mock. Provider real nunca aprova release
gate sozinho.

### Visível, configurado e selecionável são estados diferentes

- `README.md` (este arquivo)
- `VERSION.md`
- `PedroCore IA/00_MAPEAMENTO_GERAL_PEDROCORE.md`
- `PedroCore IA/MOC_PEDROCORE_IA.md`
- `PedroCore IA/MOC_MULTI_PROVIDER_SAFE_EVOLUTION.md`
- `PedroCore IA/17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7.md`
- `PedroCore IA/10-contratos/CONTRATO_ELYRA_TEXTUAL_V1.md`
- `PedroCore IA/17-multi-provider-safe-evolution/PEDROCORE_ELYRA_ONBOARDING_V1_TEXTUAL.md`
- `PedroCore IA/17-multi-provider-safe-evolution/GATE_PEDROCORE_ELYRA_ONBOARDING_V1_TEXTUAL.md`
- `PedroCore IA/MOC_QA_SAFETY_HARDENING.md`
- `PedroCore IA/MOC_ESTUDO_PEDROCORE.md`
- `PedroCore IA/00-visao-geral/README.md`
- `PedroCore IA/00-visao-geral/OBJETIVO.md`
- `PedroCore IA/03-versoes/ROADMAP.md`
- `PedroCore IA/09_STATUS_ATUAL.md`
- `PedroCore IA/07-decisoes/DECISOES_TECNICAS.md`
- `PedroCore IA/08_CHANGELOG.md`
As cinco IAs externas — Gemini, OpenAI, Claude, DeepSeek e Grok/xAI — são
**sempre visíveis** na interface, com ou sem credencial. O que muda é o estado:

| Estado | Significado |
| --- | --- |
| **Visível** | O PedroCore conhece a IA; ela aparece nas Configurações e no seletor |
| **Configurado** | O backend tem credencial (`configured` de `/api/providers`) |
| **Selecionável** | Pode conversar agora: visível **e** homologada **e** configurada |

Hoje **Gemini é a única IA habilitada para uso real**. OpenAI, Claude, DeepSeek
e Grok permanecem catalogadas e visíveis, porém indisponíveis até configuração e
homologação — aparecem desabilitadas e com o motivo, em vez de sumirem da tela.

Para habilitar uma IA já catalogada basta configurar a credencial no `.env` do
backend: a interface reage sozinha, sem alteração de código.

Os providers internos (`mock`, `local_qa`, `local_model`, `auto`) não são IAs e
ficam fora da build pública; em desenvolvimento, apenas `mock` é liberado como
destino de conversa, com selo `DEV`.

---

## Recursos da V1

- **Chat multi-provider** com modo de resposta (padrão, técnico, resumido, código).
- **Composer único**: textarea que cresce, Enter envia, Shift+Enter quebra linha,
  seletor de IA na própria barra e motivo do bloqueio sempre visível.
- **Configurações em drawer** acessível: `aria-modal`, Escape, foco gerenciado.
- **Autorização explícita de provider real**, persistida por provider e
  sobrevivendo ao recarregamento — trocar de IA descarta a anterior.
- **Ditado por voz** (Web Speech API): o áudio não é gravado, guardado nem
  enviado ao PedroCore; só o texto transcrito entra no campo, para revisão.
- **Anexos textuais** (`.txt`, `.md`, `.markdown`, `.csv`, `.json`, `.log`) com
  allowlist, limites conservadores e envio pelo contrato de artefatos existente.
- **Histórico local** no navegador, com feedback por mensagem.
- **Observabilidade técnica local** em `#/observability` — default-off e restrita
  a loopback.

Não incluído nesta versão: análise **multimodal** (imagem, PDF, DOCX). Foi
adiada formalmente para a V2 — ver `PedroCore IA/20-ux-v1/V2_MULTIMODAL.md`.

---

## Instalação

Pré-requisitos: **Python 3.12+**, **Node 22+** e `git`.

```bash
git clone <url-do-repositorio>
cd pedrocore-ia
```

### Backend

```bash
cd apps/api
python -m venv .venv
# Windows:        .venv\Scripts\activate
# Linux/macOS:    source .venv/bin/activate
pip install -e .
```

### Frontend

```bash
cd apps/web
npm install
```

---

## Configuração

```bash
cd apps/api
cp .env.example .env
```

Edite `.env` e preencha apenas o que for usar. **Sem nenhuma chave o projeto
funciona**: o provider padrão é `mock`, que não faz chamada externa.

| Variável | Para quê |
| --- | --- |
| `GEMINI_API_KEY` | Habilita o único provider real homologado |
| `PEDROCORE_CORS_ORIGINS` | Origens do frontend (default: `localhost:5173`) |
| `PEDROCORE_INTERNAL_API_KEY` | Autenticação opcional do `/api/orchestrate` |
| `PEDROCORE_CALLER_REGISTRY` | Registro de consumidores; **única** forma de um projeto externo alcançar provider real |
| `APP_ENV` | `development` por padrão; `production` fecha o caminho não autenticado |

Todas as demais flags (`local_model`, OCR, multimodal, Playwright, circuit
breaker, fallback real, observabilidade) são **default OFF** e estão
documentadas em `.env.example`.

> `.env` nunca deve ser versionado. Apenas `.env.example` vai para o Git.

---

## Execução

```bash
# Backend — http://127.0.0.1:3333
cd apps/api
python -m uvicorn app.main:app --reload --port 3333

# Frontend — http://localhost:5173
cd apps/web
npm run dev
```

Documentação interativa da API: `http://127.0.0.1:3333/docs`.

---

## Testes

```bash
# Backend
cd apps/api
python -m pytest -q

# Frontend
cd apps/web
npm test
npm run typecheck
npm run build
```

Resultado da última execução (16/08/2026):

```text
backend    751 passed, 7 skipped, 2 warnings
frontend    86 passed (6 arquivos)
typecheck   PASS
build       PASS
```

Nenhuma das suítes chama provider real ou faz requisição de rede externa.
Testes que exigiriam isso são opt-in por flags `PEDROCORE_RUN_REAL_*_TESTS` e
ficam skipped por padrão.

Validação do grafo documental:

```bash
cd apps/api
python -m app.modules.docs_graph.service
```

---

## Integrações

- **FinGuard** — consumidor homologado. Usa `provider=auto` sem escolher
  modelo; o PedroCore resolve identidade, autorização, provider e modelo. O
  FinGuard não recebe nem repassa chaves. O PedroCore não lê, escreve nem
  executa nada no repositório do FinGuard.
- **Structa** — consumidor read-only de menor privilégio: apenas a task
  `qa_report_analysis`, apenas Gemini, apenas em ambiente não produtivo e apenas
  com credencial registrada.

Adicionar um novo consumidor **não exige código novo**: basta uma entrada em
`PEDROCORE_CALLER_REGISTRY` e a política correspondente.

---

## Segurança

O modelo padrão é de **uso local**, e as garantias são proporcionais a isso.

**O que já está protegido**

- Chaves de API vivem **exclusivamente no backend**. O navegador nunca as vê:
  o `localStorage` guarda preferências e o *identificador* do provider
  autorizado — consentimento, não credencial.
- **Safe mode**: `allow_real_provider=false` por padrão.
- **Identidade fail-closed**: com registro de callers configurado, requisição
  sem credencial ou com credencial desconhecida é rejeitada. Credencial
  compartilhada não identifica projeto e nunca alcança provider real.
- Artefatos com campo de caminho são **rejeitados sem leitura**.
- Observabilidade é default-off, volátil e restrita a loopback.
- Sem vetores de XSS no frontend: o conteúdo é renderizado como texto.

**Limitações conhecidas**

- `POST /api/chat` **não exige autenticação**, por compatibilidade e para servir
  o frontend local.
- Não há **rate limiting**, controle de custo por consumidor nem teto global de
  payload.
- Não há terminação TLS própria.

Por isso: **seguro** para uso local, para o ecossistema local e para ter o
código público. **Não seguro** para expor a API na internet sem antes adicionar
autenticação obrigatória, rate limiting, teto de payload e TLS.

Detalhamento por cenário: `PedroCore IA/20-ux-v1/MODELO_DE_AMEACA.md`.
Política de reporte de vulnerabilidade: [`SECURITY.md`](SECURITY.md).

---

## Limitações

- **Deploy público**: não suportado no estado atual (ver acima).
- **Multimodal**: imagem, PDF e DOCX não são analisados. Artefatos visuais são
  registrados com aviso e sempre exigem revisão humana.
- **Multi-provider automático**: a arquitetura está concluída, mas só Gemini
  está homologado, então `auto` sempre resolve para ele. É decisão de
  homologação, não pendência técnica.
- **Cancelamento remoto**: após timeout, o PedroCore fecha a conexão local, mas
  não há prova de que a geração remota parou. Tratado como conclusão ambígua.
- **QA local** é heurística determinística, não IA — não substitui validação
  humana e não executa testes.
- O PedroCore **não é um modelo treinado**: não há fine-tuning, autoaprendizado
  nem RAG. Relatórios técnicos não treinam IA.

---

## Documentação

A documentação canônica vive em `PedroCore IA/`, como vault Obsidian navegável.

- **Entrada principal:** [`PedroCore IA/MOC_PEDROCORE_IA.md`](PedroCore%20IA/MOC_PEDROCORE_IA.md)
- Interface atual: `PedroCore IA/MOC_UX_V1.md`
- Arquitetura: `PedroCore IA/MOC_ARQUITETURA.md`
- Segurança: `PedroCore IA/MOC_SEGURANCA.md`
- Testes: `PedroCore IA/MOC_TESTES.md`
- Integrações: `PedroCore IA/MOC_INTEGRACOES.md`
- Status atual: `PedroCore IA/09_STATUS_ATUAL.md`
- Changelog: `PedroCore IA/08_CHANGELOG.md`
- Versionamento: [`VERSION.md`](VERSION.md)

Documentos históricos são preservados e identificados como tal; o estado
corrente está sempre em `09_STATUS_ATUAL.md`.

---

## Contribuindo

Ver [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licença

**Ainda não definida.** Sem um arquivo `LICENSE`, o padrão legal é que todos os
direitos ficam reservados ao autor. A escolha da licença é uma decisão pendente
do proprietário do projeto.
