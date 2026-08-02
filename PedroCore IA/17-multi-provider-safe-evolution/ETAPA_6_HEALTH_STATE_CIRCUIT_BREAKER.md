# Etapa 6 — Health state e circuit breaker

Frente: `PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION`.

Status: **implementada e validada localmente, desligada por padrão**.

## Resultado

O PedroCore agora mantém health state técnico por
`ambiente + provider + modelo`, separado de configuração, homologação,
autorização e policy. O estado é local, volátil e por processo:

```text
closed
  ├─ falhas retryable até o limiar → open
  └─ conclusão ambígua → open imediato

open
  └─ cooldown monotônico concluído → half_open

half_open
  ├─ um único probe bem-sucedido → closed
  └─ qualquer probe sem sucesso → open
```

Não existe health check externo, banco, persistência, endpoint administrativo
ou coordenação distribuída. Workers e instâncias diferentes não compartilham
estado. O reset existente é uma operação interna usada pelos testes.

## Configuração conservadora

O circuit breaker é controlado apenas por configuração interna e não aparece
no payload dos consumidores:

- `PEDROCORE_CIRCUIT_BREAKER_ENABLED`: default `false`;
- `PEDROCORE_CIRCUIT_FAILURE_THRESHOLD`: default `3`, limitado entre 1 e 100;
- `PEDROCORE_CIRCUIT_COOLDOWN_SECONDS`: default `30`, limitado entre 0,01 e
  86.400 segundos.

Com a flag desligada, o comportamento legado é preservado. A política shadow
somente consulta snapshots; ela não abre, fecha nem reserva probe. A aquisição
do probe half-open é atômica e protegida por lock no processo.

## Taxonomia e contaminação

As tentativas usam classificação estruturada, sem inferência pelo texto da
exception:

| Classificação | Efeito no circuito fechado |
| --- | --- |
| `success` | fecha e zera falhas |
| `provider_retryable` | incrementa; abre no limiar |
| `completion_ambiguous` | abre imediatamente |
| `provider_non_retryable` | não degrada health |
| `provider_pre_dispatch` | não degrada health |
| `caller_error` | não degrada health |
| `policy_error` | não degrada health |
| `internal_error` | não degrada health |

Falhas de caller, policy, configuração e execução interna não são tratadas como
evidência de indisponibilidade do provider.

## Timeout e certeza de conclusão

Os adapters externos atuais encapsulam SDKs síncronos com
`asyncio.to_thread`. `asyncio.wait_for` limita a espera do caller, mas não
prova que o trabalho na thread terminou. Um teste determinístico com
`threading.Event`, sem `sleep`, comprova que a atividade pode continuar depois
do timeout.

Por isso timeout é registrado como:

- `failure_classification=completion_ambiguous`;
- `completion_certainty=ambiguous`;
- `external_dispatch=true`;
- abertura imediata do circuito quando a feature está habilitada.

O circuit breaker impede nova aquisição local enquanto aberto, mas não cancela
nem comprova o término da chamada já despachada. Essa evidência será o gate
obrigatório da Etapa 7.

## Auditoria e observabilidade

Cada tentativa real recebe `request_id`/`audit_id`, `attempt_id`, ordinal,
provider, modelo, instante inicial, duração, dispatch externo, certeza de
conclusão, classificação e estado do circuito antes/depois. A projeção antiga
de smoke conserva seu formato quando essa telemetria estruturada não existe.

O roteador elimina candidatos com circuito `open` ou probe `half_open` ocupado.
Bloqueios acontecem antes do adapter e recuam para Mock seguro, sem chamar
provider secundário.

## Validação

- testes direcionados: `176 passed`, sem falha;
- regressão específica de contrato: `44 passed`, sem falha;
- suíte completa: `553 passed, 7 skipped, 2 warnings`;
- eval harness: `14/14`, `risk_level="none"`;
- Ruff nos arquivos alterados: aprovado;
- timeout pós-`to_thread`, concorrência de half-open e isolamento por chave
  testados com relógio fake, events, threads, fakes e spies;
- zero chamadas externas reais;
- nenhuma alteração no FinGuard, frontend, dependências ou `.env`.

## Limites preservados

- o estado não é compartilhado entre processos ou instâncias;
- não existe cancelamento cooperativo nos adapters atuais;
- circuito aberto reduz risco de uma nova chamada, mas não encerra uma chamada
  anterior;
- não existe fallback entre providers reais neste commit; o mecanismo restrito
  posterior está em [[ETAPA_7_FALLBACK_REAL_CONTROLADO]];
- apenas `gemini + gemini-3.5-flash` permanece homologado e autorizado para o
  automático real.

## Nota de evolução — OUTPUT-BUDGET-CANCELLATION-01

Este documento descreve o estado do commit `30d308f` e permanece válido como
registro histórico. Depois dele, a frente
[[18-provider-output-budget-cancellation/PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]]
alterou o caminho Gemini:

- o adapter deixou de usar `asyncio.to_thread` e passou a usar o cliente
  assíncrono nativo, com fechamento explícito;
- passou a existir timeout de transporte, sempre menor que a espera da
  orquestração;
- o cancelamento da task, do `await` e do transporte local passou a ser real.

O que **não** mudou, e é o ponto central desta etapa: fechar a conexão local
continua não provando que a geração remota parou. Timeout após dispatch segue
sendo `completion_ambiguous`/`ambiguous`, o circuito mantém o tratamento
conservador e nenhum secundário é iniciado.
