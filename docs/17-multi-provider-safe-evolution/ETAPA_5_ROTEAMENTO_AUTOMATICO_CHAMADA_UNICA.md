# Etapa 5 — Roteamento automático enforced com chamada única

Frente: `PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION`.

Status: **motor implementado e aprovado; diversificação operacional bloqueada
por ausência de segundo provider/modelo homologado**.

## Resultado

O avaliador determinístico antes exclusivo do shadow passou a ser o motor
único de decisão. Catálogo, filtros, prioridades, motivos de eliminação e
desempate são calculados uma vez; apenas o modo operacional muda:

| Modo | Comportamento |
| --- | --- |
| `legacy` | preserva a seleção anterior e é o default conservador |
| `shadow` | calcula e registra, sem controlar a execução |
| `enforced` | aplica o primeiro provider/modelo elegível |

O modo vem somente de configuração interna
`PEDROCORE_PROVIDER_ROUTING_MODE`. Consumidores não possuem campo para
controlá-lo. Valor inválido recua para `legacy` e fica registrado como
configuração inválida. A flag anterior
`PEDROCORE_SHADOW_ROUTING_ENABLED=true` continua mapeada para `shadow` quando
a configuração nova está ausente, evitando duas fontes efetivas conflitantes.

## Elegibilidade cumulativa

O candidato precisa passar por registro, implementação, configuração,
homologação do provider, autorização estática para o automático, identidade,
matriz projeto/papel/ambiente, policy, task, catálogo e homologação/autorização
do modelo, binding total e safe mode.

Configuração isolada não cria homologação. Identidade `ambiguous` continua sem
provider real. O modelo chega ao adapter como string não vazia já validada.

## Execução com chamada única

Em `provider=auto` + modo `enforced`:

```text
decisão determinística
→ primeiro candidato elegível
→ no máximo uma tentativa real
→ sucesso ou Mock seguro
```

Falha do candidato não inicia o segundo colocado. Não existe fallback entre
providers reais nesta etapa.

Seleção explícita de ferramenta técnica continua fora do ranking automático e
preserva identidade, autorização, binding, task, ambiente e safe mode.

## Homologação real disponível

Cinco providers externos possuem modelo explicitamente catalogado, mas apenas
o par abaixo está homologado e autorizado:

| Provider | Modelo | Automático real |
| --- | --- | --- |
| `gemini` | `gemini-3.5-flash` | elegível quando configurado e autorizado |
| `claude` | `claude-sonnet-4-5` | não homologado |
| `openai` | `gpt-5.2-mini` | não homologado |
| `deepseek` | `deepseek-chat` | não homologado |
| `grok` | `grok-4.3` | não homologado |

Portanto o motor enforced está pronto, mas o veredito
**multi-provider automático operacional** permanece **não**. Nenhuma
homologação foi criada para completar artificialmente a etapa.

## Auditoria e observabilidade

São registrados modo, versão da política, validade da configuração, candidatos
considerados/eliminados, provider/modelo selecionado, motivo, diferença para o
efetivo e quantidade de tentativas reais. Esses dados permanecem técnicos; o
contrato de assistente do FinGuard continua limitado a `answer`,
`suggestions` e `disclaimer`.

## Validação

- testes direcionados: `147 passed`, sem falha;
- suíte completa: `529 passed, 7 skipped, 2 warnings`;
- eval harness: `14/14`, `risk_level="none"`;
- Ruff nos arquivos alterados: aprovado;
- adapters externos substituídos por fakes/spies;
- zero chamadas externas reais;
- máximo comprovado: uma tentativa real;
- nenhuma alteração no FinGuard ou em `.env`.

## Limites preservados

- neste checkpoint da Etapa 5, health state e circuit breaker ainda não
  estavam implementados; foram entregues posteriormente na
  [[ETAPA_6_HEALTH_STATE_CIRCUIT_BREAKER]];
- fallback entre providers reais ainda não foi implementado;
- timeout ainda usa espera sobre adapters síncronos em thread;
- Etapas 6 e 7 permaneceram fora deste commit.
