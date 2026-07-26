# Etapa 1 — Catálogo e caracterização de providers

Frente: `PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION`.

Status: **implementado, passivo e sem alteração de roteamento**.

## Objetivo

Criar uma base interna, tipada e testável que descreva providers e modelos —
sem alterar qual provider é executado. O catálogo é **consultivo**: nenhum
ponto do pipeline de orquestração o consome nesta etapa.

## Onde

- `apps/api/app/modules/provider_catalog/schemas.py` — tipos e invariantes.
- `apps/api/app/modules/provider_catalog/service.py` — construção da
  caracterização a partir dos adapters realmente registrados.
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

## Segurança

`required_config_keys` guarda apenas **nomes** de variáveis de ambiente, com
invariante que recusa qualquer coisa fora do padrão `^[A-Z][A-Z0-9_]*$`.
Nenhum valor de credencial, endpoint privado ou segredo entra no catálogo,
no `snapshot()` de diagnóstico ou nos testes.

## O que esta etapa NÃO faz

- não adiciona Claude, OpenAI, DeepSeek ou Grok ao modo automático;
- não altera `AUTO_REAL_PROVIDER_CANDIDATES` (segue `("gemini",)`);
- não implementa fallback entre providers reais, retry, shadow routing,
  score dinâmico, circuit breaker ou provider/model binding;
- não altera o contrato público de `POST /api/orchestrate` nem a projeção
  consumida pelo frontend do FinGuard (`answer`, `suggestions`, `disclaimer`).
