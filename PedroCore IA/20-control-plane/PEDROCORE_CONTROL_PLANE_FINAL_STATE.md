# PedroCore — Control Plane: Estado Final

Estado factual do PedroCore ao fim das Eras 1 a 10, verificado contra o código
real em 29/08/2026. Nenhum número aqui foi copiado de relatório anterior: todos
foram recontados a partir do Git e das suítes executadas.

Decisões: [[ADR_PEDROCORE_AI_RUNTIME_LEARNING_CONTROL_PLANE]] e
[[ADR_PEDROCORE_UNIVERSAL_CONTRACTS_V1]].
Contratos: [[PEDROCORE_UNIVERSAL_CONTRACTS_REFERENCE]].
Baseline inicial: [[PEDROCORE_CURRENT_ARCHITECTURE_BASELINE]].
Migração: [[PEDROCORE_CONTROL_PLANE_MIGRATION_MAP]].

## 1. Arquitetura final

```text
                            PEDROCORE
                   (modular monolith, 1 processo)
                                │
     ┌──────────────────────────┴──────────────────────────┐
     │                                                     │
RUNTIME PLANE (32)                              LEARNING PLANE (3)
responder agora                                 aprender depois
     │                                                     │
orchestration · providers · chat                training_data
retrieval · operational_memory                  dataset_registry
report_intelligence · report_memory             training_foundation
interaction_outcomes · risk_engine                        │
safe_reuse · audit · observability                        │
evidence_platform · resilience                            │
     │                                                     │
     │        structured operational sources                │
     └──────────── evidence / contratos ───────────────────►│
                                                            │
     ┌──────────────────────────┬──────────────────────────┘
     │                          │
SHARED KERNEL (6)      CONSUMER CAPABILITIES (3)
caller_identity        elyra_textual
contracts              elyra_multimodal
project_context        elyra_learning
real_features
docs_graph
universal_contracts
```

**44 módulos**, todos com plano declarado em
`apps/api/app/architecture/planes.py` e verificados por teste. Um módulo novo
sem declaração quebra o build.

### Fluxo ponta a ponta

```text
CONSUMIDOR
   │ fato observado + capacidade declarada + evidência verificável
   ▼
Universal Contract V1  (envelope + payload tipado)
   │
   ▼
Evidence Platform      tamanho → contrato → autoridade → privacidade
   │                   → fingerprint → idempotência → persistência
   ▼
EvidenceRecord         Operational Source. NUNCA Training Candidate.
   │
   │ seleção MANUAL por administrador
   ▼
Learning Plane         eligibility · privacy · provenance · authorization
   │
   ▼
TrainingCandidate      PROPOSED → AUTHORIZED → … → CONSUMED
   │
   │ readiness real
   ▼
Dataset Registry       definição livre · materialização gated
   │
   ▼
Training Foundation    baseline → comparação → promoção → rollback
```

Cada seta é uma fronteira com recusa própria. Não existe caminho curto entre
as pontas.

## 2. Contratos públicos

### API — 39 paths

| Grupo | Paths |
|---|---|
| Infra | `GET /`, `GET /health` |
| Assistant | `POST /api/chat`, `GET /api/providers` |
| Orquestração | `POST /api/orchestrate` |
| Report Memory | 7 |
| Interaction Outcomes | 2 |
| Operational Memory + Retrieval | 3 |
| Risk Engine | 8 |
| Safe Reuse | 1 |
| Observability | 4 |
| Training Candidate | 7 |
| **Evidence Platform** | **2** (Eras 4 e 6) |

### Contratos universais V1 — congelados

| Contrato | Versão | Fingerprint congelado |
|---|---|---|
| Project Capability Manifest | `pedrocore-capability-manifest/v1` | `sha256:e4bdfa62…` |
| Quality Evidence (QEC) | `pedrocore-quality-evidence/v1` | `sha256:ee63c68b…` |
| Execution Outcome | `pedrocore-execution-outcome/v1` | `sha256:25f62fcf…` |
| Learning Source | `pedrocore-learning-source/v1` | `sha256:77021aec…` |
| Integration Envelope | `pedrocore-integration/v1` | `sha256:5e9a5c35…` |

`tests/test_contract_freeze.py` compara o JSON Schema de cada um a cada
execução. Alterar a forma de um contrato V1 **quebra o build**.

## 3. Política de breaking change

| Classe | O que é | O que exige |
|---|---|---|
| **ADITIVA** | campo opcional com default; valor novo em enum | atualizar o fingerprint congelado, com o motivo no commit. Não muda a versão. |
| **BREAKING** | campo obrigatório novo; remoção de campo; mudança de tipo; mudança de semântica | criar `.../v2`. A v1 permanece suportada até existir migration path comprovado. **Nunca se altera a v1 no lugar.** |
| **DEPRECATED** | versão em fim de vida | continua aceita, respondendo com aviso. Deprecação avisa, não derruba. |
| **UNKNOWN** | versão que o servidor não conhece | recusada, fail-closed. Nunca adivinhada. |

### Mudança de contrato público nas Eras 4–10

Comparação Era 3 → final, campo a campo:

| Item | Antes | Depois | Classe |
|---|---|---|---|
| paths | 37 | 39 | **aditiva** — 2 novas, 0 removidas, 0 alteradas |
| schemas | 156 | 163 | **aditiva** — 7 novos, 0 removidos |
| `TrainingSourceType` | 8 valores | 9 valores | **aditiva** — `+evidence_record`; nenhum valor removido, nenhuma outra chave alterada |

**Zero breaking change.** Nenhum consumidor precisa mudar coisa alguma.

## 4. Banco e migrations

| Migration | Conteúdo |
|---|---|
| `0001_operational_reports.sql` | Report Memory |
| `0002_interaction_outcomes.sql` | Interaction Outcomes |
| `0003_operational_memory.sql` | Operational Memory |
| `0004_operational_memory_retrieval.sql` | índices de retrieval |
| `0005_training_candidates.sql` | Candidate Store |
| `0006_evidence_records.sql` | **Evidence Registry (Era 4)** |
| `0007_outbox_entries.sql` | **Outbox durável (Final Hardening)** |
| `0008_dataset_registry.sql` | **Definições e versões de dataset (Final Hardening)** |

Todas aditivas, com checksum, aplicadas por
`python -m app.modules.report_memory.migrate`. O runner descobre arquivos novos
por glob ordenado — `0006` entrou sem alteração de código.

`0006` mantém o padrão: `PRIMARY KEY (project_id, evidence_record_id)`,
`UNIQUE (project_id, kind, fingerprint)` para dedup garantido pelo banco sob
concorrência, e índice único **parcial** de idempotência por projeto.
**Isolamento de projeto é chave primária, não filtro de aplicação.**

## 5. Estado de dataset e treinamento

```text
DATASET_NOT_READY          ← correto e esperado
CONTROL_PLANE_READY        ← governança completa e testada
```

- `automatic_collection`: `Literal[False]` em todas as 9 origens. Não é flag
  desligada — é tipo que faz o Pydantic **recusar** `True`.
- `PEDROCORE_DATASET_READINESS_MIN_AUTHORIZED` não configurada →
  `READINESS_VOLUME_POLICY_NOT_CONFIGURED` mantém `DATASET_NOT_READY`.
  Prontidão nunca é inferida por contagem.
- Candidate Store e Evidence Registry: default `off`, fail-closed, sem fallback
  silencioso para memória.
- Nenhuma população foi fabricada. Nenhum treino foi executado. Nenhum modelo
  foi promovido.

## 6. Arquivos das Eras 1–10

Contados no Git (`7fc650c..HEAD`), não estimados:

| Era | Criados | Modificados |
|---|---|---|
| 1–2 — Control Plane | 6 | 4 |
| 3 — Universal Contracts | 13 | 9 |
| 4 — Evidence Platform | 8 | 4 |
| 5 — Learning Governance V2 | 1 | 6 |
| 6 — Resiliência | 4 | 2 |
| 7 — Dataset Control Plane | 4 | 1 |
| 8 — Training Foundation | 4 | 1 |
| 9 — Contract Freeze | 1 | 1 |
| **Total** | **41** | **16** |

Zero arquivos movidos. Zero removidos. Zero depreciados.

> **Correção de drift.** Relatórios anteriores desta frente publicaram duas
> contagens erradas, ambas corrigidas aqui e nos documentos de origem: a Era 2
> declarou "Criados (5)" enumerando 6 (real: 6), e a Era 3 declarou
> "Modificados: 8" enumerando 9 (real: 9) e "Criados: 12" (real: 13). A
> divergência vinha de contar uma pasta de documentação como uma linha só.

## 6.1 Durabilidade (Final Hardening)

| Componente | Antes | Depois |
|---|---|---|
| Outbox | apenas em memória | `DurableOutboxStore` (arquivo, atômico) + `PostgreSQLOutboxStore` |
| Dataset Registry | apenas em memória | `LocalJsonDatasetRegistryRepository` + migration `0008` |

**Escrita atômica.** Ambos gravam em arquivo temporário e movem com
`os.replace`. Escrever direto no destino tem uma janela em que o arquivo está
truncado — e se o processo morre exatamente ali, o outbox volta corrompido. O
modo de falha que ele existe para resolver seria a causa da perda.

**O que conta como restart.** Instância nova, mesmo armazenamento. Reutilizar o
mesmo objeto em memória não prova nada: ele nunca perdeu o estado. Um dos
testes vai além e grava em **subprocesso separado**, que morre antes de o teste
ler o arquivo.

### Wiring de produção

A durabilidade não vale como classe disponível — vale como caminho realmente
percorrido. A implementação é escolhida pela **mesma** variável do resto do
sistema, `PEDROCORE_REPORT_MEMORY_PERSISTENCE`:

| modo | outbox | dataset registry | durável? |
|---|---|---|---|
| `off` | **recusa** fail-closed | **recusa** fail-closed | — |
| `memory` | `OutboxStore` | `InMemory...` | não (explícito) |
| `local_json` | `DurableOutboxStore` | `LocalJson...` | **sim** |
| `postgresql` | `PostgreSQLOutboxStore` | **recusa** (não implementado) | sim / — |

`off` recusa em vez de cair em memória: um outbox que silenciosamente não
persiste promete uma garantia de entrega que não tem, e o consumidor descobre
no primeiro restart — com dado já perdido. `memory` continua disponível, mas
só por escolha explícita.

O registry PostgreSQL **recusa** em vez de cair para arquivo. As tabelas
existem na migration `0008`, mas o repositório não foi escrito; cair para
arquivo faria o operador acreditar que a governança está no banco de que ele
faz backup quando está em um arquivo local que ninguém copia.

### Corrupção: detectar, preservar, degradar

A primeira versão tratava arquivo ilegível como store vazio. Isso é pior do que
não persistir: o consumidor conclui que não há nada pendente, e a escrita
seguinte apaga entregas que ninguém chegou a ver.

| Antes | Depois |
|---|---|
| corrompido → fila vazia | corrompido → estado **degradado** |
| registro inválido → descartado | registro inválido → **corrupção** |
| escrita seguinte sobrescrevia | escrita **recusada** até revisão |
| — | original preservado + **cópia** em quarentena |

A quarentena é cópia e não movimentação: mover liberaria o caminho original e a
escrita seguinte criaria um arquivo novo por cima — o desaparecimento que se
quer impedir. `clear()` é a saída explícita, depois que alguém revisou.

O diagnóstico carrega caminho, motivo e índice do registro — **nunca o
conteúdo**. Um outbox corrompido contém payloads de evidência, e reproduzi-los
na mensagem os colocaria no log de quem tentava protegê-los.

**Provado por 39 testes** (`tests/test_durability.py` e
`test_durability_hardening.py`): enqueue, persistência,
sobrevivência de pendente, cronograma de backoff preservado, retry após
restart, acknowledgement preservado, duplicata sem duplo registro, dead-letter
revisável, requeue, reconciliação após restart, e arquivo corrompido que não
derruba o consumidor.

**Verificação por mutação**, três sabotagens deliberadas, todas restauradas:

| Sabotagem | Reprovou |
|---|---|
| carregamento do disco desligado | 9 de 18 |
| corrupção volta a virar lista vazia | 5 de 21 |
| quarentena move em vez de copiar | 4 de 21 |
| serviço volta a default em memória | 2 de 21 |

**Persistir governança não fabricou população.** Um teste dedicado confirma que
`DATASET_NOT_READY` continua valendo depois do reload, e que nenhuma versão de
dataset foi materializada.

## 7. Testes

| Suíte | Comando | Resultado |
|---|---|---|
| Backend integral | `python -m pytest -q` | **1340 passed, 21 skipped, 0 failed** |
| Lint | `python -m ruff check .` | **All checks passed!** |
| Frontend | `npm run build` (`tsc -b && vite build`) | **PASS** |
| Grafo documental | `docs_graph.build_graph()` | **íntegro** |

Evolução: 1152 (baseline Era 3) → 1273 (Era 10) → 1319 → **1340** = **+188**, todos novos.
Zero regressão em todas as Eras.

### Os 21 skips

Idênticos desde a Era 1, mesmos blockers, nenhum novo:

- **13** exigem `PEDROCORE_TEST_POSTGRES_URL` (PostgreSQL de teste ausente);
- **8** são opt-in de recurso real (`PEDROCORE_RUN_REAL_*`), todos default
  `false` por segurança.

Nenhum é falha mascarada. Nenhum apareceu ou desapareceu durante as Eras.

### Verificação por mutação

Guardas críticos não foram assumidos — a regressão que cada um existe para
impedir foi **reintroduzida de propósito** e o teste reprovou, com o arquivo
restaurado em seguida:

| Guarda | Regressão injetada | Resultado |
|---|---|---|
| Fronteira de planos (Era 2) | import de topo Runtime→Learning | 2 testes reprovaram |
| Anti-acoplamento (Era 3) | `project_id == "finguard"` no core | 1 teste reprovou |
| Contract freeze (Era 9) | `quality_score` na QEC | 2 testes reprovaram |
| Durabilidade (Hardening) | carregamento do disco desligado | 9 testes reprovaram |
| Corrupção (Verification) | corrompido volta a virar vazio | 5 testes reprovaram |

## 8. Segurança

- **Nenhum segredo real versionado.** Único arquivo de ambiente rastreado é
  `.env.example`, com todos os campos de chave vazios.
- Scanner de privacidade (segredo, credencial, token, PII, financeiro, caminho
  pessoal, conteúdo bruto) agora é **único e compartilhado**: os padrões vivem
  no Shared Kernel e servem tanto a ingestão quanto a promoção a candidato.
  Duas cópias divergiriam na primeira vez que alguém acrescentasse um padrão em
  um lado só.
- Achados de privacidade reportam **código, categoria e caminho — nunca o
  valor**. Devolver o trecho colocaria o segredo no log, na resposta de erro e
  no relatório de auditoria.
- Mensagens de erro de contrato **não ecoam o payload recusado**.
- Mensagens de bloqueio deixaram de nomear consumidores: um aviso que nomeia
  um sistema revela a terceiros quais o PedroCore conhece.
- Defaults fail-closed em toda a linha: mock por default, providers reais off,
  observabilidade off, persistência off, artifact reader off, OCR/multimodal/
  Playwright off, routing `legacy`.

## 9. Dívida técnica registrada

| # | Dívida | Local | Era sugerida |
|---|---|---|---|
| D1 | `_PROJECTS` e `PROJECT_MANIFESTS` descrevem o mesmo consumidor por ângulos diferentes | `project_context/` | unificação futura |
| D2 | `class Config` do Pydantic v1 deprecado | `app/core/config.py:4` | manutenção |
| D3 | BOM UTF-8 em 2 arquivos | `providers/mock_provider.py`, `tests/test_chat.py` | manutenção |
| D4 | Contratos `elyra-*/v1` não migrados para os universais | `elyra_*/` | Era com esse objetivo |

**D5 e D6 foram resolvidas no Final Hardening** e saíram desta tabela.

A dívida original dizia que Dataset Registry e outbox viviam só em memória, e a
justificativa era que persistir o vazio seria custo sem retorno. A revisão
humana apontou que o raciocínio estava errado para o outbox — e estava.

O outbox em memória protege contra o **servidor** cair, mas não contra o
**consumidor** cair, que é exatamente onde o dado se perde: o processo grava a
entrega pendente, morre antes de entregar, e a fila some com ele. Um outbox que
não sobrevive ao próprio processo é um buffer, não um outbox. A propriedade
central da Era 6 estava provada pela metade.

Para o Dataset Registry o argumento também não se sustentava: o que se persiste
ali é **metadata de governança** — quem declarou qual escopo, sob qual política,
e o que entrou em cada versão. Uma decisão que morre com o processo vira boato,
e a linhagem que torna um modelo auditável desaparece junto. Persistir
governança não fabrica população.

## 10. O que NÃO foi feito

Por decisão explícita de escopo, e não por falta de tempo:

- nenhum treinamento, fine-tuning, LoRA ou SFT real;
- nenhum dataset canônico materializado;
- nenhuma integração com Hugging Face ou GPU cloud;
- nenhum modelo promovido a produção;
- nenhuma migração de FinGuard, Structa ou Elyra;
- nenhum broker ou microsserviço;
- nenhum push, merge, tag, release ou mudança de visibilidade.
