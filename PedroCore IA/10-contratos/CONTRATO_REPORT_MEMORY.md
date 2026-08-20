# Contrato — Report Memory

Frente: `PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01` (Fase B)
Atualizado em: 20/08/2026

Links: [[CONTRATO_ECOSYSTEM_ASSISTANT]] | [[../14-intelligence-layer/REPORT_MEMORY]] | [[../14-intelligence-layer/REPORT_INTELLIGENCE_FOUNDATION]]

## 1. Princípio

**Relatórios técnicos NÃO treinam IA, NÃO fazem fine-tuning e NÃO alteram comportamento automaticamente.** Eles viram sinais, histórico e contexto consultável (memória técnica). Toda resposta de ingestão carrega o warning `REPORT_MEMORY_IS_NOT_TRAINING`.

## 2. Configuração (default OFF)

| Flag | Default | Valores |
|---|---|---|
| `PEDROCORE_REPORT_MEMORY_PERSISTENCE` | `off` | `off` \| `memory` \| `local_json` |
| `PEDROCORE_REPORT_MEMORY_DIR` | vazio | diretório para `local_json` (obrigatório nesse modo) |

- `off` — nada é guardado nem consultado (ingest responde `status="disabled"`).
- `memory` — repositório in-process volátil (máx. 50 entradas por projeto).
- `local_json` — um arquivo JSON por projeto no diretório configurado pelo operador; conteúdo sanitizado (segredos redigidos com `[REDACTED]`); dados de runtime não devem ser commitados; nunca grava em `.env`.

## 3. Rotas

Autorização: as três rotas reutilizam `caller_identity`. O `project_id` do
payload/path é apenas uma alegação e precisa coincidir com o projeto da
credencial registrada; o papel exigido é `technical_tool`. Credencial ausente,
inválida, sem capacidade ou de outro projeto falha fechado (`401`/`403`).

Compatibilidade LEGACY:

- sem autenticação configurada, o modo dev/local existente continua ativo e
  identificado como `local_trusted`; produção exige identidade registrada;
- `PEDROCORE_INTERNAL_API_KEY` continua autenticando, mas não prova projeto:
  sua identidade `ambiguous` fica restrita ao namespace
  `shared_or_unknown` e não acessa projetos concretos.

### V1 LEGACY — `POST /api/reports/analyze` e `/api/reports/ingest`

Recebe `TechnicalReportInput` e aplica o adapter V1 → V2 antes da lógica de
domínio. `analyze` não persiste; `ingest` preserva o comportamento histórico.

### V2 — `POST /api/reports/v2/analyze` e `/api/reports/v2/ingest`

Recebe `IntelligenceReportEnvelopeV2` (`schema_version=2.0`) com payload tipado
`interaction_quality`, `qa_evidence`, `risk_analysis` ou `execution_outcome`.
Versões desconhecidas são rejeitadas. `producer` é validado contra o
`credential_id`; o payload não pode forjar provenance.

No mesmo projeto, repetir `report_id` retorna `status="duplicate"`,
`stored=false` e `REPORT_DUPLICATE_IGNORED`, sem criar uma segunda entrada.

### `GET /api/project-memory/{project_id}/summary`

Snapshot agregado (`ProjectMemorySnapshot`): `last_known_status`, `last_report_at`, `latest_commit`, `latest_branch`, `completed_milestones`, `unresolved_risks`, `recurring_signals`, `next_recommended_steps`, `confidence`, `source_count`. Sem leitura de repositório externo; memória isolada por `project_id`.

## 4. Integração com /api/orchestrate

`context_from_memory=true` no payload (default `false`):

- consulta a memória do `project_id` resolvido pelo `origin_system`;
- anexa snapshot **limitado (máx. 2.000 chars) e sanitizado** como seção `[Memória técnica]` do prompt;
- marca `memory_used=true` e adiciona `REPORT_MEMORY_USED`;
- memória desabilitada → `REPORT_MEMORY_DISABLED`; sem registros → `REPORT_MEMORY_EMPTY` (ambos com `memory_used=false`).

Nunca há leitura de arquivo/repositório: só o que foi previamente ingerido por payload.

## 5. Segurança

- `producer`, papel e ambiente vêm da identidade resolvida, nunca do payload;
  observabilidade registra somente `credential_id`/fingerprint não secreto.
- Caller registrado do projeto A não analisa, grava nem consulta memória do
  projeto B; tentativas retornam `CALLER_ORIGIN_MISMATCH`.
- Credencial LEGACY não pode transformar `project_id` declarado em provenance;
  tentativa contra projeto concreto retorna `CALLER_IDENTITY_AMBIGUOUS`.
- Nenhum segredo é armazenado: sanitização redige padrões `api_key/token/password/senha/secret/chave = valor`.
- Nenhuma rota aceita path ou arquivo local.
- Nenhum provider é chamado por essas rotas.
- Sinais `critical`/`high` (`provider_real_used`, `database_safety_risk`, ...) exigem revisão humana (`evaluation.requires_human_review=true`).
