# Etapa 1 — Catálogo e caracterização de providers

Frente: `PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION`.

Status: **concluída; a entrega original foi passiva e não alterou o
roteamento**. O catálogo de modelos foi posteriormente corrigido no commit
`8c97004`.

## Objetivo

Criar uma base interna, tipada e testável que descreva providers e modelos —
sem alterar qual provider é executado. O catálogo é **consultivo**: nenhum
ponto do pipeline de orquestração o consome nesta etapa.

## Onde

- `apps/api/app/modules/provider_catalog/schemas.py` — tipos e invariantes.
- `apps/api/app/modules/provider_catalog/service.py` — caracterização dinâmica
  dos providers realmente registrados e catálogo explícito `_MODEL_CATALOG`.
- `apps/api/tests/test_provider_catalog.py` — estrutura, estados e invariantes.
- `apps/api/tests/test_provider_auto_characterization.py` — congelamento do
  comportamento automático atual.

## Estados separados

`registered`, `implemented`, `configured`, `homologation`,
`authorized_for_auto` e `health` são campos distintos e nunca inferidos um do
outro. Em particular:

- ter chave configurada **não** homologa, **não** autoriza e **não** torna
  saudável;
- existir adapter **não** significa estar configurado;
- provider não implementado não pode estar configurado, homologado nem
  elegível.

## Saúde

Chamadas reais estão proibidas nesta frente, então nenhum provider real pode
ser marcado como `healthy`: o estado inicial é `unknown` e o invariante recusa
`healthy` sem `health_evidence` explícita. Apenas os caminhos determinísticos
em processo (`mock`, `local_qa`) declaram `healthy` com evidência
`in_process_deterministic`.

## Providers caracterizados

| Provider | Categoria | Homologação | Auto | Observação |
| --- | --- | --- | --- | --- |
| `gemini` | `real_external` | `homologated_real` | sim | único candidato real do automático |
| `claude` | `real_external` | `not_homologated` | não | fora do automático |
| `openai` | `real_external` | `not_homologated` | não | fora do automático |
| `deepseek` | `real_external` | `not_homologated` | não | fora do automático |
| `grok` | `real_external` | `not_homologated` | não | fora do automático |
| `mock` | `simulated` | `homologated_internal` | não | fallback seguro |
| `local_qa` | `local_deterministic` | `homologated_internal` | não | único confiável em release gate |
| `local_model` | `local_generative` | `not_homologated` | não | opt-in, default OFF, sem transport |

`auto` não é provider: é modo de seleção e não pertence ao catálogo.

## Reconciliação posterior do catálogo de modelos

O commit `8c97004` separou a caracterização de provider da definição de
modelos. A seleção configurada em runtime (`settings`, ambiente ou
`adapter.default_model`) informa somente um identificador candidato; ela
**não** cria, registra, implementa, homologa nem autoriza um modelo.

Os modelos reconhecidos pelo PedroCore existem apenas no catálogo explícito e
imutável `_MODEL_CATALOG`. Cada entrada declara proprietário, registro,
implementação, homologação, autorização, default e compatibilidade de task.
O catálogo falha cedo se um identificador/alias tiver proprietário ambíguo ou
se um provider tiver mais de um default explícito.

Assim, os estados precisam ser lidos separadamente:

- provider configurado não implica modelo conhecido;
- modelo conhecido não implica homologado;
- modelo homologado não implica autorizado;
- a homologação do provider não homologa automaticamente seus modelos.

Na entrega original da Etapa 1 o catálogo era consultivo. As Etapas 3 e 4
passaram a consumir essas definições, sem transformar configuração runtime em
fonte de verdade.

## Segurança

`required_config_keys` guarda apenas **nomes** de variáveis de ambiente, com
invariante que recusa qualquer coisa fora do padrão `^[A-Z][A-Z0-9_]*$`.
Nenhum valor de credencial, endpoint privado ou segredo entra no catálogo,
no `snapshot()` de diagnóstico ou nos testes.

## O que a entrega original desta etapa NÃO fez

- não adiciona Claude, OpenAI, DeepSeek ou Grok ao modo automático;
- não altera `AUTO_REAL_PROVIDER_CANDIDATES` (segue `("gemini",)`);
- não implementou fallback entre providers reais, retry, shadow routing,
  score dinâmico, circuit breaker ou provider/model binding; binding e shadow
  foram entregues separadamente nas Etapas 3 e 4;
- não altera o contrato público de `POST /api/orchestrate` nem a projeção
  consumida pelo frontend do FinGuard (`answer`, `suggestions`, `disclaimer`).
