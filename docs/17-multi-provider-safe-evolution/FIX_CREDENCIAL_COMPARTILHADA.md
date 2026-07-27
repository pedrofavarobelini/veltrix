# Fix de segurança — credencial compartilhada não autoriza provider real

Frente: `PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION` (correção da Etapa 2).

Status: **vulnerabilidade confirmada e corrigida**.

## A falha

A Etapa 2 (`64e6c59`) tratava a API key global compartilhada como identidade
suficiente. O contexto compartilhado recebia `caller_role=technical_tool` e
`project_id=None`, e `validate_origin_claim()` então derivava o projeto da
alegação `origin_system` do payload. A matriz autorizava
`finguard × technical_tool × qualquer ambiente × gemini`. Resultado:

```
caller com a chave global compartilhada
→ declara origin_system=finguard
→ identidade aceita sem prova
→ assume o projeto FinGuard
→ passa na matriz de autorização
→ alcança o adapter real do Gemini
```

Confirmado empiricamente por sonda determinística (spy de adapter, sem rede)
antes da correção:

```
project_id: finguard
provider_used: gemini
caller_role: technical_tool
origin_validation: not_enforced
project_id_authenticated: finguard
adapters chamados: ['gemini']
```

O spoofing que a Etapa 2 deveria eliminar continuava aberto.

## A correção

### 1. Força de identidade explícita

Novo eixo `IdentityStrength` no contexto autenticado:

- `registered` — credencial em `PEDROCORE_CALLER_REGISTRY`, vinculada a
  projeto, papel, ambiente e origens permitidas;
- `local_trusted` — sem autenticação interna configurada (dev/local), operador
  local;
- `ambiguous` — API key global compartilhada, ou ausência de credencial com
  registro ativo.

Invariantes recusam estados incoerentes: identidade ambígua não pode ter papel
técnico nem assumir projeto; credencial registrada precisa declarar projeto e
origens; contexto local não pode fixar projeto.

### 2. Credencial compartilhada em menor privilégio

A chave global passa a receber `caller_role=common_consumer`,
`project_id=shared_or_unknown` e `identity_strength=ambiguous`. Ela continua
**autenticando** a requisição (compatibilidade transitória), mas não prova
projeto algum.

### 3. Identidade separada do contexto de policy

`OriginClaimResult` passa a devolver dois valores distintos:

- `identity_project_id` — projeto **provado**; único valor que alimenta a
  matriz de autorização e a auditoria de identidade;
- `context_project_id` — projeto usado para policy/tasks (Project Context),
  preservando o contrato público existente.

Para o caller ambíguo, `identity_project_id` é sempre `shared_or_unknown`,
qualquer que seja a origem declarada. A alegação é registrada como
`not_trusted` — nunca convertida em identidade.

### 4. Matriz com identidade e ambiente explícitos

A regra genérica `finguard × ambos os papéis × todos os ambientes × gemini`
foi eliminada. Agora:

| Identidade | Projeto | Papéis | Ambientes | Providers |
| --- | --- | --- | --- | --- |
| `registered` | `finguard`, `finguard-local` | ambos | dev/local/test/qa/staging | `gemini` |
| `registered` | `finguard`, `finguard-local` | ambos | produção (regra própria) | `gemini` |
| `registered`, `local_trusted` | `pedrocore` | `technical_tool` | dev/local/test/qa/staging | `gemini` |

`ambiguous` não consta de nenhuma regra e é negado antes de qualquer
diagnóstico operacional.

### 5. Violação de identidade ≠ falha operacional

| Situação | Resultado |
| --- | --- |
| Gemini autorizado, porém indisponível | Mock seguro, `PROVIDER_REAL_UNAVAILABLE` |
| Caller ambíguo tentando provider real | Negação segura antes do adapter, `CALLER_IDENTITY_AMBIGUOUS` |
| Consumidor comum escolhendo provider | Bloqueio explícito, `CALLER_PROVIDER_SELECTION_NOT_ALLOWED` |
| Modelo arbitrário | Bloqueio explícito, `CALLER_MODEL_SELECTION_NOT_ALLOWED` |
| Spoofing de origem (credencial registrada) | Bloqueio explícito, `CALLER_ORIGIN_MISMATCH` |

## Consequências no contrato

- Provider real para **FinGuard** passa a exigir credencial registrada. Com a
  chave global, o FinGuard continua atendido por Mock e `local_qa`, sem
  qualquer chamada real.
- O modo dev/local (sem autenticação configurada) mantém o comportamento
  preexistente **apenas para o próprio projeto `pedrocore`** e fora de
  produção; alegar `finguard` sem credencial registrada não autoriza nada.
- O contrato público de `POST /api/orchestrate` e a projeção do frontend
  (`answer`, `suggestions`, `disclaimer`) permanecem inalterados.
- `AUTO_REAL_PROVIDER_CANDIDATES` continua `("gemini",)`.

## Limitações remanescentes

- Nenhuma credencial registrada está provisionada neste repositório: hoje o
  ambiente opera em modo ambíguo (chave global) ou dev/local. Provisionar
  `PEDROCORE_CALLER_REGISTRY` é pré-requisito para o FinGuard voltar a usar
  provider real.
- Em modo dev/local sem autenticação, quem alcança o endpoint age como
  operador local do `pedrocore` (fora de produção). Deploys expostos devem
  configurar autenticação — a camada de identidade não substitui autenticação
  ausente.

---

## Navegacao

- [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]]
- [[MOC_FECHAMENTOS]]
