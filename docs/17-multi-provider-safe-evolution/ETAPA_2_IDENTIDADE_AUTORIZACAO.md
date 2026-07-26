# Etapa 2 — Identidade autenticada e autorização por projeto

Frente: `PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION`.

Status: **implementado, fail-closed, sem alteração do provider automático**.

## Objetivo

A identidade do caller passa a ser derivada da **credencial autenticada**, e
providers reais passam a depender de **autorização explícita por projeto,
papel e ambiente**. `origin_system` deixa de ser fonte soberana de identidade.

## Onde

- `apps/api/app/modules/caller_identity/` — contexto autenticado, resolução de
  credencial, validação da alegação de origem e restrições por papel.
- `apps/api/app/modules/provider_authorization/` — matriz fail-closed.
- `apps/api/app/modules/orchestration/service.py` — integração no pipeline.
- `apps/api/app/modules/orchestration/router.py` — resolução da credencial.
- `apps/api/app/modules/audit/` — auditoria separando identidade e alegação.
- `apps/api/tests/test_caller_identity_authorization.py` — testes da etapa.

## Ordem soberana da identidade

```
credencial autenticada
→ registro seguro de caller
→ project_id
→ caller_role
→ environment
```

`origin_system` continua aceito no payload por compatibilidade, mas apenas
como **alegação validada**. Divergência entre a origem declarada e a identidade
autenticada é **rejeitada** (`CALLER_ORIGIN_MISMATCH`), nunca corrigida em
silêncio: o valor declarado continua ecoado no contrato, e a auditoria mostra
os dois lados.

## Registro de callers

Variável de ambiente `PEDROCORE_CALLER_REGISTRY`, com JSON de entradas:

```json
[
  {
    "credential_id": "finguard-app",
    "api_key": "<credencial>",
    "project_id": "finguard",
    "role": "common_consumer",
    "environment": "production",
    "allowed_origins": ["finguard"]
  }
]
```

- `credential_id` é o identificador **não secreto** usado em auditoria; se
  omitido, vira um fingerprint truncado (`fp_` + 12 hex de SHA-256), que não
  permite reconstruir nem reutilizar a chave.
- `role` desconhecido cai em `common_consumer` (menor privilégio).
- `allowed_origins` omitido restringe a credencial à própria origem do projeto.
- Registro presente porém ilegível é **fail-closed**: nenhuma identidade é
  derivada (`CALLER_REGISTRY_INVALID`).

## Credencial compartilhada — limitação registrada

Sem `PEDROCORE_CALLER_REGISTRY`, o PedroCore continua com **uma única API key
global** (`PEDROCORE_INTERNAL_API_KEY`) ou sem autenticação interna em modo
dev/local. Nesse caso:

> A infraestrutura de identidade foi implementada, porém o isolamento
> operacional entre múltiplos projetos depende do provisionamento de
> credenciais distintas.

A identidade é marcada como compartilhada, a validação de origem é registrada
como `not_enforced` e isso aparece explicitamente na auditoria e na
observabilidade. `origin_system` **não** é usado para compensar uma credencial
indistinguível: ele apenas continua sendo a alegação já existente.

## Papéis

| Papel | Pode | Não pode |
| --- | --- | --- |
| `common_consumer` | `provider=auto`, `mock`, `local`, `local_qa` | escolher provider real, enviar modelo, mudar `project_id`, falsificar `origin_system` |
| `technical_tool` | seleção explícita **dentro** da matriz e das políticas existentes | contornar matriz, safe mode, policy ou homologação |

Nenhum papel administrativo foi criado: não há justificativa arquitetural
existente para ele.

## Matriz de autorização

```
project_id + caller_role + environment + provider → permitido ou negado
```

Default **negar**. Combinações registradas:

| Projeto | Papéis | Ambientes | Providers |
| --- | --- | --- | --- |
| `finguard`, `finguard-local` | `common_consumer`, `technical_tool` | dev/local/test/qa/staging/produção | `gemini` |
| `pedrocore` | `technical_tool` | dev/local/test/qa/staging | `gemini` |

Tudo o mais é negado: Claude, OpenAI, DeepSeek e Grok não são autorizados para
nenhum projeto, papel ou ambiente; origem desconhecida não alcança provider
real; `pedrocore` em produção não está registrado de propósito.

## Cadeia cumulativa para uma chamada real

```
caller autenticado
+ project_id conhecido
+ papel permitido
+ ambiente permitido
+ provider permitido na matriz
+ provider implementado
+ provider configurado
+ provider homologado
+ task permitida
+ safe mode permitindo
+ allow_real_provider=true
```

`allow_real_provider` continua existindo e continua obrigatório, mas é
**consentimento da requisição**, nunca autorização: sozinho, jamais libera
provider real.

## Negar não vira chamada real

Negação de autorização produz **fallback Mock seguro**, com
`PROVIDER_NOT_AUTHORIZED_FOR_PROJECT` / `PROVIDER_NOT_HOMOLOGATED`. O
candidato negado nunca é substituído por outro provider real: não há fallback
entre providers reais, e `provider=auto` continua Gemini-only.

## Auditoria e observabilidade

Registrados sem segredos: `credential_id`, `authenticated`,
`project_id_authenticated`, `caller_role`, `environment`,
`origin_system_declared`, `origin_validation`, `provider_selection_mode`,
`provider_requested`, `provider_selected`, `provider_used`,
`authorization_result` e `authorization_reason_code`. Nunca são registrados
API key, token, header completo, segredo ou hash completo reutilizável.

## Contrato público

`POST /api/orchestrate` mantém as chaves existentes (os campos novos de
auditoria são aditivos e retrocompatíveis). A projeção consumida pelo frontend
do FinGuard continua limitada a `answer`, `suggestions` e `disclaimer` — sem
nenhum metadado técnico novo.
