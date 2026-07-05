# Exemplos de uso da API — MVP (PEDROCORE-IMPLEMENT-01/02/03)

Exemplos seguros, sem segredo real, para consumo de `POST /api/chat` e `POST /api/orchestrate`. Nenhum destes exemplos chama provider real.

## 1. `/api/chat` legado, com Mock

Requisição mínima, compatível com clientes antigos (sem nenhum campo novo):

```json
POST /api/chat
{
  "message": "Explique o que é o PedroCore IA",
  "mode": "tecnico",
  "provider": "mock"
}
```

Resposta esperada (resumida):

```json
{
  "answer": "Resposta tecnica simulada do MockProvider...",
  "provider": "mock",
  "model": "mock-v1",
  "fallback_used": false,
  "status": "ok",
  "task_type": "general_chat",
  "qa_skeleton": null
}
```

## 2. `/api/orchestrate` com `local_qa` para `release_gate_review`

Payload com artefato textual de teste passando, usando o pseudo-provider local (sem IA externa, sem rede):

```json
POST /api/orchestrate
{
  "message": "Pode avançar para release?",
  "origin_system": "finguard",
  "task_type": "release_gate_review",
  "provider": "local_qa",
  "mode": "tecnico",
  "artifacts": [
    {
      "type": "qa_report",
      "name": "pytest.txt",
      "content": "125 passed, 0 failed. Build successful."
    }
  ]
}
```

Resposta esperada (resumida):

```json
{
  "status": "ok",
  "provider_used": "local_qa",
  "qa": {
    "status": "pass",
    "risk_level": "low",
    "can_advance": true,
    "analysis_source": "local_text_heuristic"
  },
  "release_gate": {
    "can_advance": true,
    "blocked_reason": null,
    "risk_level": "low"
  },
  "audit": {
    "audit_id": "...",
    "provider_requested": "local_qa",
    "provider_used": "local_qa",
    "safe_mode_blocked": false,
    "can_advance": true
  }
}
```

## 3. Provider real bloqueado pelo Safe Mode

Payload solicitando um provider real sem autorização explícita:

```json
POST /api/chat
{
  "message": "Teste",
  "provider": "gemini",
  "allow_real_provider": false
}
```

(`allow_real_provider` ausente equivale a `false` — o mesmo resultado ocorreria sem esse campo.)

Comportamento esperado: o Gemini **nunca é chamado**. A resposta vem via fallback Mock, com:

```json
{
  "provider": "mock",
  "requested_provider": "gemini",
  "fallback_used": true,
  "safe_mode_blocked": true,
  "warning_codes": ["PROVIDER_REAL_BLOCKED"]
}
```

## 4. Artifact rejeitado por conter campo de caminho de arquivo

Payload tentando enviar um artefato referenciando um arquivo local via metadata:

```json
POST /api/orchestrate
{
  "message": "Analise este arquivo",
  "provider": "mock",
  "task_type": "qa_report_analysis",
  "artifacts": [
    {
      "type": "qa_report",
      "name": "relatorio.md",
      "metadata": { "path": "C:\\qualquer\\caminho\\relatorio.md" }
    }
  ]
}
```

Comportamento esperado: o PedroCore **nunca lê o arquivo indicado**. O artefato é rejeitado:

```json
{
  "status": "blocked",
  "warning_codes": ["ARTIFACT_PATH_REJECTED", "..."],
  "qa": { "can_advance": false }
}
```

## 5. Autenticação interna de `/api/orchestrate`

- Se `PEDROCORE_INTERNAL_API_KEY` **não estiver configurada** no ambiente: `/api/orchestrate` funciona em modo dev/local e a resposta inclui o warning `INTERNAL_AUTH_NOT_CONFIGURED`.
- Se `PEDROCORE_INTERNAL_API_KEY` **estiver configurada**: toda chamada a `/api/orchestrate` exige o header `X-PedroCore-Api-Key` com o valor correto.
  - Header ausente → `401` com `error_code: "INTERNAL_AUTH_MISSING"`.
  - Header incorreto → `401` com `error_code: "INTERNAL_AUTH_INVALID"`.
  - Header correto → requisição processada normalmente.
- `POST /api/chat` **nunca exige** essa chave, independente da configuração.

Exemplo de chamada autenticada (chave ilustrativa, nunca um valor real):

```
POST /api/orchestrate
Header: X-PedroCore-Api-Key: <valor-configurado-no-ambiente>
```

A chave em si nunca é retornada em nenhuma resposta da API.
