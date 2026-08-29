# PedroCore — Control Plane Migration Map

Mapa de classificação arquitetural e registro do que a Era 2 efetivamente
mudou. Evidência de base: [[PEDROCORE_CURRENT_ARCHITECTURE_BASELINE]].
Decisão: [[ADR_PEDROCORE_AI_RUNTIME_LEARNING_CONTROL_PLANE]].
Contexto anterior: [[MOC_ARQUITETURA]].

## 1. Diagrama factual resultante

```text
                          PEDROCORE
                    (modular monolith, 1 processo)
                               │
        ┌──────────────────────┴──────────────────────┐
        │                                             │
   RUNTIME PLANE                                LEARNING PLANE
   responder agora                              aprender depois
        │                                             │
   orchestration          structured operational      training_data
   providers        ────── sources / evidence ──────► (Dataset Foundation)
   chat                    (contratos estáveis)
   retrieval                                          eligibility
   operational_memory                                 privacy
   report_intelligence                                provenance
   interaction_outcomes                               authorization
   risk_engine                                        lifecycle
   safe_reuse                                         readiness
   audit / observability
        │                                             │
        └──────────────► SHARED KERNEL ◄──────────────┘
                    caller_identity, contracts,
                 project_context, real_features,
                          docs_graph

                     CONSUMER CAPABILITIES
              elyra_textual, elyra_multimodal, elyra_learning
           (única fronteira onde regra de projeto é legítima)
```

A seta é de mão única por decisão e por teste: o Learning Plane consome
evidência do Runtime Plane, e não o contrário.

## 2. Classificação arquitetural — 40 módulos

Todos os módulos foram classificados. Nenhum ficou `UNKNOWN`.
Nenhum foi classificado como `REMOVE`: não havia justificativa concreta para
remover coisa alguma, e remover sem justificativa é destruição, não limpeza.

### Runtime Plane (29 módulos) — todos `KEEP`

| Módulo | Ação | Nota |
|---|---|---|
| `orchestration` | **ADAPT** | única alteração de código da Era 2 (import tardio) |
| `task_router` | KEEP | |
| `policy_enforcement` | KEEP | |
| `prompt_builder` | KEEP | contém acoplamento P2 (`finguard`) — dívida registrada |
| `output_budget` | KEEP | |
| `providers` | KEEP | 6 providers + registry + contrato local |
| `provider_authorization` | KEEP | |
| `provider_binding` | KEEP | |
| `provider_catalog` | KEEP | |
| `provider_health` | KEEP | |
| `shadow_routing` | KEEP | |
| `chat` | KEEP | |
| `artifacts` | KEEP | |
| `artifact_reader` | KEEP | |
| `retrieval` | KEEP | serve `/api/operational-memory/retrieve` |
| `operational_memory` | KEEP | |
| `report_intelligence` | KEEP | |
| `report_memory` | KEEP | |
| `interaction_outcomes` | KEEP | |
| `risk_engine` | KEEP | inclui Execution Contracts |
| `safe_reuse` | KEEP | |
| `qa_analysis` | KEEP | |
| `qa_response` | KEEP | |
| `visual_qa` | KEEP | |
| `evaluation` | KEEP | |
| `eval_harness` | KEEP | |
| `intelligence_layer` | KEEP | |
| `exploration` | KEEP | opt-in, default-off |
| `ocr` | KEEP | opt-in, default-off |
| `audit` | **MOVE (lógico)** | reclassificado — ver §4 |
| `observability` | **MOVE (lógico)** | reclassificado — ver §4 |

### Learning Plane (1 módulo) — `KEEP`

| Módulo | Ação | Nota |
|---|---|---|
| `training_data` | KEEP | 2.642 loc; Dataset Foundation exclusiva do PedroCore |

O Learning Plane inteiro em um módulo não é defeito. Dataset Foundation,
eligibility, privacy, provenance, authorization, lifecycle e readiness
compartilham versão de política (`training-acquisition-v1`,
`dataset-foundation-v1`, `dataset-readiness-v2`). Fatiar em pastas o que é
versionado em conjunto criaria fronteira falsa e custo real de navegação.

### Shared Kernel (5 módulos) — todos `KEEP`

`caller_identity`, `contracts`, `project_context`, `real_features`,
`docs_graph`. Critério verificado por teste: **não depende de nenhum plano.**

### Consumer Capabilities (3 módulos) — todos `KEEP`

`elyra_textual`, `elyra_multimodal`, `elyra_learning`. São adaptadores de
contrato por consumidor. É legítimo que conheçam o nome do seu consumidor —
essa é a razão de existirem separados do core genérico.

## 3. O que a Era 2 mudou

### MOVED — nenhum arquivo

Zero movimentação física. A decisão está justificada na ADR: mover 40 módulos
para `app/runtime/` e `app/learning/` reescreveria imports em centenas de
arquivos e colocaria 1085 testes verdes em risco para melhorar apenas a
aparência da árvore de diretórios. A fronteira que importa é a de dependência.

`audit` e `observability` foram movidos de agrupamento **lógico**, não de
pasta: nenhum arquivo mudou de lugar.

### ADAPTED — 1 arquivo

`app/modules/orchestration/service.py`

O import de `training_data.acquisition` saiu do topo do módulo e passou a ser
feito dentro de `_elyra_learning_outcome`, a única função que o usa.
`training_data.schemas` permanece no topo por ser contrato puro — não arrasta
repository, Candidate Store nem driver PostgreSQL.

Efeito: uma falha de importação do Learning Plane deixou de derrubar a
importação do Runtime Plane. O invariante "se o Learning Plane falhar, o
Assistant ainda funciona" passou a valer **também em tempo de importação**, e
não apenas em tempo de execução.

Zero mudança de comportamento: mesma função, mesmos objetos, mesmas exceções.

### CREATED — 4 arquivos

| Arquivo | Papel |
|---|---|
| `app/architecture/__init__.py` | pacote novo |
| `app/architecture/planes.py` | declaração das fronteiras (dado, não prosa) |
| `tests/test_control_plane_boundaries.py` | 12 testes que cobram a fronteira |
| `PedroCore IA/20-control-plane/` (3 docs) | baseline, ADR, este mapa |

### PRESERVED — tudo o mais

- 37 paths públicos: idênticos em path, método, schema e código de erro;
- 5 migrations, todas as constraints e índices: intocados;
- 4 repositories PostgreSQL: intocados;
- políticas de eligibility, privacy, provenance, authorization: intocadas;
- `automatic_collection = Literal[False]`: intocado;
- matriz de autorização de providers, caller registry, task types: intocados;
- frontend `apps/web`: **não afetado**, nenhum arquivo tocado;
- FinGuard, Structa e Elyra: nenhuma alteração necessária do lado deles.

### DEPRECATED — nenhum módulo

Nada foi depreciado. Nenhum módulo se mostrou morto, redundante ou substituído.

## 4. Uma reclassificação que o teste forçou

`audit` e `observability` foram inicialmente declarados no Shared Kernel — a
intuição sendo que auditoria e observabilidade são infraestrutura transversal.

O teste `test_shared_kernel_does_not_depend_on_either_plane` reprovou:

```text
audit/service.py            -> provider_binding
observability/service.py    -> evaluation
observability/gemini_smoke.py -> orchestration, provider_binding, providers
```

Elas não são neutras. Elas auditam e observam a **execução**, que é assunto do
Runtime Plane. A declaração foi corrigida para refletir o código real.

Isto é o valor da fronteira executável, demonstrado no primeiro uso: a
classificação errada durou minutos em vez de meses, e foi o código que a
corrigiu, não uma revisão.

## 5. Dívida técnica registrada

| # | Dívida | Local exato | Era sugerida |
|---|---|---|---|
| P2a | `caller.project_id == "elyra"` no core genérico | `orchestration/service.py:380` | Project Capability Manifest |
| P2b | `project_id == "finguard"` no core genérico | `prompt_builder/service.py:25` | Project Capability Manifest |
| P4 | 4 `DOCUMENTATION_DRIFT` | ver baseline §11 | contínua |
| P5 | `class Config` do Pydantic v1 deprecado | `app/core/config.py:4` | manutenção |
| P6 | BOM UTF-8 em 2 arquivos | `providers/mock_provider.py`, `tests/test_chat.py` | manutenção |

**P2 não foi corrigida nesta Era, deliberadamente.** A migração de FinGuard,
Structa e Elyra e o Project Capability Manifest estão explicitamente fora de
escopo. Corrigir o sintoma sem o mecanismo substituto — política por
contrato/configuração — trocaria um acoplamento conhecido e testado por um
acoplamento novo e não testado. Fica registrado com precisão de linha.

**P6 foi descoberta pelos testes novos.** O parser AST da fronteira falhou ao
ler dois arquivos que começam com BOM UTF-8. O interpretador Python tolera BOM,
então não há defeito em produção; o leitor dos testes passou a usar
`utf-8-sig`. Os dois arquivos não foram reescritos — reescrever fonte que
funciona para agradar um parser seria risco sem retorno.

## 6. Regras de dependência agora executáveis

Doze testes em `tests/test_control_plane_boundaries.py`:

**Completude da declaração**
1. todo módulo em disco tem plano declarado — módulo novo sem declaração quebra o build;
2. todo módulo declarado existe em disco — declaração obsoleta quebra o build;
3. os agrupamentos são disjuntos e cobrem tudo;
4. `training_data` pertence ao Learning Plane (Dataset Ownership).

**Direção da dependência**
5. o Learning Plane nunca importa o motor do Runtime (orchestration, providers, chat…);
6. o Runtime Plane não importa o Learning Plane, salvo exceção declarada;
7. cada exceção declarada é real, usada e justificada em ≥80 caracteres;
8. `orchestration` mantém o import da maquinaria de treinamento **tardio**;
9. o Shared Kernel não depende de nenhum plano.

**Invariante de disponibilidade**
10. o Runtime Plane carrega com o Learning Plane sabotado (em subprocesso isolado);
11. o Assistant responde com o Candidate Store desabilitado;
12. o Candidate Store permanece fail-closed quando desabilitado.

### Verificação por mutação

A eficácia dos guardas não foi assumida. O import de topo foi **reintroduzido
deliberadamente** e a suíte de fronteira foi executada:

```text
FAILED test_orchestration_defers_the_learning_plane_import
FAILED test_runtime_plane_imports_without_the_learning_machinery
2 failed, 10 passed
```

O arquivo foi restaurado em seguida. Um guarda que passa mas não reprova a
regressão que existe para impedir é decoração; este reprova.

### Uma armadilha encontrada no próprio teste

A primeira versão do teste de disponibilidade sabotava o import **no processo
do pytest**, apagando entradas de `sys.modules` e reimportando. Isso substituía
singletons que outros testes já seguravam e produziu 11 falhas por poluição de
estado global — falhas que passavam isoladamente e quebravam em suíte.

A correção foi rodar a prova em **subprocesso**. Isolamento de processo é o
único jeito honesto de perguntar "este módulo carrega sem aquele?" sem
corromper a sessão que faz a pergunta.

## 7. Compatibilidade

Nenhuma mudança de contrato. Nenhuma camada de compatibilidade foi necessária
porque nada quebrou. Nenhum caminho de migração é exigido de consumidores.
