# Contrato — Interaction Outcomes

Frente: `PEDROCORE-INTERACTION-OUTCOMES` — IMPLEMENTED
Atualizado em: 20/08/2026

Links: [[CONTRATO_REPORT_MEMORY]] | [[../14-intelligence-layer/INTERACTION_OUTCOMES]]

## 1. Entrada

`InteractionOutcomeInput` usa `schema_version="1.0"` e `extra="forbid"`.
Versões futuras ou campos não declarados são rejeitados, incluindo qualquer
tentativa de enviar conteúdo bruto (`input_text`, `answer`) ou provenance
privilegiada (`caller_role`, `environment`).

Campos de correlação e execução:

- `outcome_id`, `conversation_id`, `message_id`, `audit_id`;
- `project_id`, `producer`, `task_type`;
- `input_signature`, `context_signature`;
- `provider`, `model`, `response_strategy`;
- `response_characteristics`, `fallback_used`, `regeneration_used`;
- `feedback`, `accepted`, `rejected`, `quality_signals`, `created_at`.

Invariantes:

- signatures no formato `sha256:<64 hex>`;
- `accepted=true` e `rejected=true` simultâneos são inválidos;
- `created_at` exige timezone;
- `producer` deve coincidir com o `credential_id` autenticado;
- `project_id` deve coincidir com o projeto da credencial registrada.

## 2. Rotas

- `POST /api/interaction-outcomes`: ingere ou retorna duplicata idempotente;
- `GET /api/interaction-outcomes/{project_id}`: consulta paginada com filtros
  opcionais `conversation_id` e `message_id`;
- `DELETE /api/interaction-outcomes/{project_id}`: deleção explícita e isolada.

As rotas exigem `technical_tool` registrado para projetos concretos. Credencial
de outro projeto recebe 403. LEGACY não prova projeto concreto e permanece
restrito a `shared_or_unknown`.

## 3. Respostas e falhas

- primeira ingestão: `status="ok"`, `stored=true`;
- repetição: `status="duplicate"`, `stored=false`,
  `INTERACTION_OUTCOME_DUPLICATE`;
- persistência `off`: `status="disabled"`, `stored=false`;
- banco/configuração/schema indisponível: HTTP 503
  `INTERACTION_OUTCOME_PERSISTENCE_UNAVAILABLE`, sem fallback local.

## 4. Persistência e lifecycle

Os modos e flags são compartilhados com Operational Persistence. PostgreSQL
usa campos relacionais para isolamento/correlação/lifecycle/timestamps e JSONB
para a representação tipada completa. O lifecycle inicial é `active`; esta
etapa não promove, resolve nem transforma outcomes em regras.
