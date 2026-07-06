# Contrato de integração FinGuard → PedroCore (fase de contrato/payload fake)

Frente: `PEDROCORE-IMPLEMENT-04 — Bloco 8`.

## 1. Objetivo

Definir, do lado do PedroCore, o contrato de integração pelo qual o FinGuard (projeto externo) poderá enviar solicitações de análise QA. Nesta fase a integração é **somente por contrato e payload fake**: nada é executado no FinGuard e nada é lido do repositório real do FinGuard.

## 2. O que o FinGuard pode enviar

`POST /api/orchestrate` com:

- `origin_system`: `"finguard"` ou `"finguard-local"`;
- `task_type`: um dos permitidos (ver seção 4);
- `message`: descrição da solicitação;
- `provider`: recomendado `"local_qa"` (análise local determinística); `"mock"` para resposta conversacional;
- `allow_real_provider`: deve ser omitido ou `false` (provider real permanece bloqueado por padrão);
- `artifacts`: lista de artefatos **textuais por payload** (`type`, `name`, `content`, `metadata` sem campos de caminho);
- `metadata`/`context`: dados auxiliares (ex.: `environment`, `source`, `routes`).

Task types permitidos para origem FinGuard:

```text
qa_report_analysis
qa_failure_diagnosis
release_gate_review
exploratory_test_plan
manual_exploration_report
assisted_exploration_review
artifact_summary
technical_explanation
```

## 3. O que o PedroCore retorna

Resposta estruturada do `/api/orchestrate`: `status`, `answer`, `warning_codes`, `warnings` (com severidade), `error_code`, `blocked_reason`, `task_warnings` (compatibilidade), `qa` (skeleton preenchido por heurística local quando aplicável), `release_gate` (para `release_gate_review`), `visual_qa_analysis` (stub, quando houver artefato visual), `exploration` (para tasks exploratórias) e `audit` não persistente completo.

## 4. Exemplo de payload fake

```json
{
  "origin_system": "finguard",
  "task_type": "qa_report_analysis",
  "message": "Analisar relatório QA fake do FinGuard.",
  "provider": "local_qa",
  "allow_real_provider": false,
  "artifacts": [
    {
      "type": "text",
      "name": "finguard-qa-fake.txt",
      "content": "125 passed, 0 failed. Build successful."
    }
  ],
  "metadata": { "environment": "fake", "source": "contract-test" }
}
```

## 5. Exemplo de resposta (resumida)

```json
{
  "status": "ok",
  "project_id": "finguard",
  "provider_used": "local_qa",
  "qa": {
    "status": "pass",
    "risk_level": "low",
    "can_advance": true,
    "analysis_source": "local_text_heuristic"
  },
  "audit": { "origin_system": "finguard", "safe_mode_blocked": false }
}
```

## 6. Segurança

Para payloads com origem FinGuard:

- FinGuard é tratado como **read-only** (`read_only=true`, `can_execute_commands=false`, `can_write_files=false`);
- campos de caminho (`path`, `file_path`, `absolute_path`, etc.) em metadata são **rejeitados** (`ARTIFACT_PATH_REJECTED`) e o Artifact Reader é **explicitamente indisponível para origem FinGuard** (`ARTIFACT_READER_PATH_NOT_ALLOWED`), mesmo se habilitado globalmente;
- o próprio Artifact Reader bloqueia qualquer caminho que contenha "finguard";
- provider real permanece bloqueado por padrão (`PROVIDER_REAL_BLOCKED` quando solicitado sem autorização);
- release gate continua conservador (mock/fallback/risco alto/evidência insuficiente sempre bloqueiam);
- nenhum comando é executado; nenhuma escrita é permitida; nenhum banco é acessado;
- task fora da lista permitida gera `PROJECT_TASK_NOT_ALLOWED`; fluxos críticos não permitidos e tasks/payloads perigosos são bloqueados por policy forte no contrato final controlado.

## 7. Limitações

- Análise QA é heurística textual local determinística — não substitui validação humana.
- Artefatos visuais só geram stub com exigência de revisão humana.
- Exploração é assistida (plano/manual) — nada é executado.

## 8. O que ainda não foi implementado

- Chamadas reais partindo do FinGuard (cliente HTTP no repositório do FinGuard).
- Autenticação dedicada por sistema chamador (hoje existe apenas a API key interna opcional do `/api/orchestrate`).
- Leitura de qualquer arquivo do FinGuard.
- QA visual real, OCR e Playwright.

## 9. Integração real futura

A integração real será feita em frente separada: o FinGuard ganhará um cliente HTTP que monta os payloads deste contrato e envia para `POST /api/orchestrate` do PedroCore (com `X-PedroCore-Api-Key` quando a chave interna estiver configurada), tratando `warning_codes`, `blocked_reason` e `release_gate` na esteira de QA dele.

## 10. Trabalho futuro no repositório FinGuard (frente separada)

- Criar cliente HTTP do PedroCore.
- Gerar/exportar relatórios QA em texto para envio por payload.
- Tratar respostas (gate bloqueado, warnings críticos) no fluxo de release do FinGuard.
- Configurar a API key interna no ambiente do FinGuard.

## 11–14. Confirmações explícitas desta fase

11. **Esta fase não acessa o repositório real do FinGuard** — nenhum arquivo do FinGuard é lido; caminhos contendo "finguard" são bloqueados em duas camadas (orquestração e reader).
12. **Esta fase não executa comandos no FinGuard** — o PedroCore não executa comandos de nenhuma origem; `suggested_commands` são apenas strings.
13. **Esta fase não altera banco real** — não há qualquer acesso a banco de dados; menções a banco real/produção em artefatos geram risco `critical` e bloqueio de avanço.
14. **Provider real continua bloqueado por padrão** — `allow_real_provider=false` é o default; o bloqueio gera `PROVIDER_REAL_BLOCKED` e, em release gate, `RELEASE_GATE_BLOCKED`.
