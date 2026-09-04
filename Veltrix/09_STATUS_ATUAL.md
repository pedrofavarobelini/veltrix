# Veltrix — Status Atual

Atualizado em: 03/09/2026

## ESTADO CORRENTE — CONGELADO

```text
VELTRIX FINALIZATION      = PASS
VELTRIX FUNCTIONAL FREEZE = ACTIVE
GITHUB PUBLICATION        = CONFIRMED
HUMAN_VISUAL_ACCEPTANCE   = PASS
HUMAN_RUNTIME_ACCEPTANCE  = PASS
```

Fechamento canônico: [[19-encerramento-final/VELTRIX_FINAL_FUNCTIONAL_GATE]].

O Veltrix **não está em uma frente ativa de manutenção**. Ele está
**congelado**. Correção trivial, ajuste cosmético, redesign e refatoração sem
ganho concreto não reabrem o projeto. Uma reabertura precisa responder *sim* a:
a mudança aumenta uma capacidade real do Veltrix, ou é necessária para ele
operar como núcleo de outro sistema?

O Final Functional Gate corrigiu o último defeito funcional observado em
homologação: no chat interativo, uma falha do provider real deixou de ser
substituída silenciosamente por uma resposta do Mock. Depois dele, o Pedro
exercitou o produto em execução e registrou `HUMAN_RUNTIME_ACCEPTANCE = PASS`
— Gemini selecionado, autorizado, respondendo de verdade, exibido como Gemini,
e o drawer de Configurações sem colisões.

Todas as seções abaixo permanecem: são o histórico acumulado das frentes, cada
uma verdadeira sobre a data em que foi escrita.

## VELTRIX — FECHAMENTO FINAL

O produto se chama **Veltrix**. Estado completo em
[[17-veltrix/VELTRIX_FINAL_STATE]]; o que mudou de nome e o que foi preservado
em [[17-veltrix/MIGRACAO_PEDROCORE_VELTRIX]].

Fechado neste ciclo: durabilidade das registries de plataforma (migration
0011), Disaster Recovery provado contra PostgreSQL real, e o rename completo
com aliases de compatibilidade para comando, variavel de ambiente e cabecalho
de credencial.

Contratos V1 congelados: intactos. Tabelas historicas: preservadas.
Consumidores nao foram migrados naquela frente de rename, por escopo;
integracoes posteriores permanecem registradas nas secoes historicas abaixo.

## PLATFORM EVOLUTION — 12 EVOLUCOES IMPLEMENTADAS

As doze evolucoes de plataforma aprovadas estao implementadas e testadas.
Estado real, evolucao por evolucao, em
[[16-plataforma/PLATFORM_EVOLUTION_FINAL_STATE]].

Resumo: Consumer SDK, Policy Engine, Control Center, Evaluation Plane V2,
Model Registry com promocao por evidencia, Shadow Mode, roteamento explicavel
por qualidade/custo/latencia, registry versionado de prompts e configuracoes,
trilha de auditoria com correlacao, SLO com estado explicito, matriz de
compatibilidade e Disaster Recovery com restauracao PROVADA.

Invariantes preservadas e agora executaveis no Policy Engine:
`automatic_collection = false`, `Operational Data != Training Candidate`, e
execucao nunca delegada ao core.

Contratos V1 congelados: intactos. OpenAPI: aditivo. UI React: nao alterada.
Rename PedroCore -> Veltrix: CONCLUIDO no fechamento final.

## PUBLICADO — repositorio publico sob Apache-2.0

`HUMAN_VISUAL_ACCEPTANCE = PASS`. O design e a UX final foram homologados pelo
Pedro em 03/09/2026 e o repositorio foi publicado em
`github.com/pedrofavarobelini/veltrix`.

A publicacao passou por higienizacao de watermark, sanitizacao do historico
Git e um gate de release verificado: CI verde, grafo documental integro,
secret scan limpo e Apache-2.0 consistente entre LICENSE, `pyproject.toml` e
`package.json`. O historico pre-sanitizacao ficou preservado em repositorio
privado separado e nao e publico.

O Veltrix entrou em **manutencao** naquele momento; apos o Final Functional
Gate ele passou a **FUNCTIONAL FREEZE = ACTIVE**. Ver a secao "ESTADO CORRENTE" no topo.

## UX FINAL + PROJECT REGISTRY — HOMOLOGADO

Ultima frente funcional antes do public-release gate. Homologada.

O Risk Console passou a ter tres estados exclusivos — ENTRADA, REVISAO DE
CONTEXTO e RESULTADO. No resultado a ordem e gate, resumo da operacao,
principais riscos, por que e o que fazer; toda a evidencia continua inteira em
seis abas, uma renderizada por vez. Nada foi removido: o que mudou foi quanto
aparece antes de alguem pedir.

O Project Registry substituiu o Capability Manifest como fonte da lista de
projetos. Seis projetos-semente, criacao e edicao pelo console, persistencia
com Protocol + InMemory + LocalJson + PostgreSQL e migration aditiva 0012. Um
projeto criado pelo usuario e analisavel como qualquer outro; sem manifesto, os
fatos ausentes ficam UNKNOWN, e nenhuma capacidade e deduzida do nome.

A guarda de analise deixou de exigir a capability `risk_analysis` e passou a
exigir projeto registrado e ativo — guarda de identidade, nao de capacidade.

Decisao de risco inalterada: ha teste de paridade comparando gate, dimensoes,
raio de impacto, cenarios, achados e recomendacoes. Nao existe sincronizacao
com GitHub; `repository_url` e metadado.

Guias: [[15-risk-engine/RISK_CONSOLE]] e [[15-risk-engine/PROJECT_REGISTRY]].

## RISK ENGINE V2 — ENCERRADO (CHECKPOINT HISTORICO: motor + produto)

O motor foi fechado em R0–R5 e, no fechamento de produto, ganhou interface
propria: Risk Console (TUI), CLI (`veltrix risk`; `pedrocore` permanece alias)
e a porta HTTP do contrato
universal (`POST /api/risk/universal/analyze`). Guia de uso em
[[15-risk-engine/RISK_CONSOLE]].

Os 22 casos de persistencia antes `skip` foram executados contra PostgreSQL
descartavel real: migrations 0009 e 0010, insert/read, durabilidade,
idempotencia, conflito, isolamento de projeto, historico e metrica de blast.

A UI React principal nao teve layout alterado. O rename PedroCore -> Veltrix
fora desta frente; a marca do console esta centralizada em
`app/modules/risk_console/branding.py`.

## RISK ENGINE V2 — R0 a R5 — READY (CHECKPOINT HISTORICO)

Motor de risco encerrado como V2. Os cinco problemas objetivos do baseline
foram fechados com evidencia: persistencia propria do dominio Risk (P1),
simulacao relevante ao payload (P2), metrica de alcance explicavel (P3),
protecao de bypass de gate provada por teste (P4) e contrato universal de
submissao de risco (P5).

Os cinco contratos V1 congelados permanecem byte a byte intactos: a submissao
de risco entrou como contrato PROPRIO — `pedrocore-risk-request/v1` — em vez de
alterar o schema do envelope de integracao.

Validacao: `1443 passed, 26 skipped, 0 failed`; Ruff PASS; frontend 117 passed;
OpenAPI 39 paths, alteracoes apenas aditivas (8 campos opcionais em 2 schemas).

Naquele checkpoint, o proximo encerramento era o rename para Veltrix. Ele foi
executado depois e esta confirmado no topo deste documento.

## LICENCA — APACHE 2.0

O repositorio passou a ser licenciado sob a Apache License 2.0 (SPDX
`Apache-2.0`), com metadata em `pyproject.toml` e `package.json`. A escolha
de licenca era a ultima pendencia humana antes da publicacao.

Correcao junto: `pip install -e .` falhava por descoberta ambigua de pacotes
(`app` e `migrations` no mesmo nivel) — defeito pre-existente que o passo de
instalacao da CI teria encontrado na primeira execucao.

## PEDROCORE-CONTROL-PLANE — ERAS 4 A 10 — PASS (CHECKPOINT HISTORICO)

Evidence Platform, Learning Governance V2, resiliencia de integracao, Dataset
Control Plane, Evaluation/Training Foundation e Contract Freeze concluidos.

Estado arquitetural: `CONTROL_PLANE_READY`, coexistindo com
`DATASET_NOT_READY` — que continua sendo o resultado correto, porque nao existe
populacao real autorizada e nenhuma foi fabricada.

Contratos V1 congelados por fingerprint de schema. Politica de breaking change
definida: aditiva nao muda versao, breaking exige v2 com a v1 mantida, versao
desconhecida e recusada fail-closed.

Contrato publico: 37 -> 39 paths (2 aditivas, 0 removidas, 0 alteradas), 156 ->
163 schemas, e uma unica alteracao aditiva (`TrainingSourceType` ganhou
`evidence_record`). Zero breaking change.

FINAL HARDENING: o outbox e o Dataset Registry passaram a ser DURAVEIS. O
outbox em memoria protegia contra o servidor cair, mas nao contra o consumidor
cair — e e ai que o dado se perde. Migrations 0007 e 0008 aditivas; 18 testes
de restart real, um deles gravando em subprocesso que morre antes da leitura.
`DATASET_NOT_READY` continua valendo: persistir governanca nao fabrica populacao.

FINAL DURABILITY VERIFICATION: duas lacunas fechadas. A implementacao duravel
nunca era construida fora de teste — agora ha factory ligada a mesma variavel
de persistencia do resto do sistema, com `off` recusando fail-closed em vez de
cair em memoria. E corrupcao deixou de virar store vazio: o arquivo ilegivel
entra em estado degradado, o original e preservado com copia em quarentena, e a
escrita e recusada ate revisao.

Validacao: `1340 passed, 21 skipped, 0 failed` (+188 desde a Era 3, todos
novos); Ruff integral PASS; `npm run build` PASS; grafo documental integro.
Os 21 skips sao os mesmos blockers ambientais/opt-in desde a Era 1.

Estado final detalhado: [[PEDROCORE_CONTROL_PLANE_FINAL_STATE]].

## PEDROCORE-UNIVERSAL-CONTRACTS-01 — ERA 3 PASS (CHECKPOINT HISTORICO)

Cinco contratos universais V1 criados e versionados, sem dependencia semantica
de nenhum consumidor: Project Capability Manifest, Quality Evidence (QEC),
Execution Outcome, Learning Source e o envelope Veltrix Integration.

Fronteira de autoridade explicita: o consumidor relata fato observado
(`observed_*`, `producer_asserted_*`) e nunca emite julgamento. Tentar enviar
`eligibility`, `authorized`, `training_candidate`, `quality_score` ou
`automatic_collection` — em qualquer profundidade e em qualquer grafia — recusa
a requisicao inteira com `CONTRACT_AUTHORITY_VIOLATION`.

Learning Source NAO e Training Candidate: submeter uma fonte nao concede
elegibilidade, autorizacao, status de candidato, pertinencia a dataset nem
readiness. Toda promocao continua no Learning Plane. `automatic_collection`
permanece `Literal[False]` e a readiness permanece `DATASET_NOT_READY`.

Os quatro acoplamentos por nome de projeto no core generico foram migrados para
capability/trait declarativos — dois deles (`artifact_reader` e o adaptador
Playwright) nao constavam do relatorio da Era 1. A migracao corrigiu um bug
latente: `finguard-local` nunca recebia a regra de seguranca porque a
comparacao `== "finguard"` nao o alcancava.

Validacao: `1152 passed, 21 skipped, 0 failed` (+55 = exatamente os contract
tests novos); Ruff integral PASS; OpenAPI identico byte a byte a Era 2 (37
paths, 156 schemas, zero breaking change); grafo documental integro.

Documentos: [[ADR_PEDROCORE_UNIVERSAL_CONTRACTS_V1]],
[[PEDROCORE_UNIVERSAL_CONTRACTS_REFERENCE]].

## PEDROCORE-CONTROL-PLANE-01 — ERA 1 PASS / ERA 2 PASS (CHECKPOINT HISTORICO)

O Veltrix passou a ter duas fronteiras internas declaradas e verificadas:
**Runtime Plane** (responder agora) e **Learning Plane** (aprender depois),
mais Shared Kernel e Consumer Capabilities. Continua modular monolith: um
processo, um `pyproject`, um `app.main`. Nenhum microsservico.

A fronteira e dado, nao prosa: `apps/api/app/architecture/planes.py` declara o
plano dos 40 modulos e `tests/test_control_plane_boundaries.py` cobra a
declaracao e a direcao da dependencia em 12 testes. Modulo novo sem plano
declarado quebra o build; import Runtime -> Learning sem excecao justificada
tambem.

Unica alteracao de codigo funcional: `orchestration/service.py` passou a
importar `training_data.acquisition` de forma TARDIA, dentro de
`_elyra_learning_outcome`. O invariante "se o Learning Plane falhar, o
Assistant ainda funciona" passou a valer tambem em tempo de importacao.

Dataset Ownership reafirmado: a Dataset Foundation e exclusiva do Veltrix;
projetos externos produzem fontes e evidencias. `automatic_collection`
permanece `Literal[False]` e a readiness observada permanece
`DATASET_NOT_READY`.

Validacao: baseline `1085 passed, 21 skipped`; pos-migracao
`1097 passed, 21 skipped, 0 failed` (+12 = exatamente os testes novos, zero
regressao). Ruff integral PASS. OpenAPI identico byte a byte (37 paths, 156
schemas). Grafo documental 158 documentos / 838 links / zero violacoes. Zero
alteracao de banco, migration, contrato publico ou frontend.

Documentos: [[ADR_PEDROCORE_AI_RUNTIME_LEARNING_CONTROL_PLANE]],
[[PEDROCORE_CURRENT_ARCHITECTURE_BASELINE]],
[[PEDROCORE_CONTROL_PLANE_MIGRATION_MAP]].

## PEDROCORE-ELYRA-ONBOARDING-V1-TEXTUAL — PASS (CHECKPOINT HISTORICO)

O Veltrix reconhece `origin_system=elyra` por credencial registrada,
`project_id=elyra` e papel `common_consumer`. A única capability habilitada é
`wellbeing_report_interpretation`, com input `elyra-textual-input/v1`, output
`elyra-textual-output/v1`, correlation e idempotência fail-closed.

CI usa mock determinístico. O modo real exige `provider=auto`,
`allow_real_provider=true`, `allow_mock_fallback=false`, seleciona somente
Gemini homologado em ambiente não produtivo e rejeita provider/modelo
respondente divergente. Multimodal, learning, prompt livre, mídia, memória e
acesso a dados Elyra permanecem desabilitados.

Validação offline: suíte focada `44 passed, 1 skipped`; backend integral `959
passed, 21 skipped, 2 warnings`; Ruff integral PASS; eval `14/14`,
`risk_level=none`; grafo 155 documentos/822 links/zero violações; zero chamadas
externas. Gate:
[[17-multi-provider-safe-evolution/GATE_PEDROCORE_ELYRA_ONBOARDING_V1_TEXTUAL]].
Contrato: [[10-contratos/CONTRATO_ELYRA_TEXTUAL_V1]].

## FECHAMENTO DOCUMENTAL FINAL — ERAS 1 A 3

Documento canônico:
[[19-encerramento-final/PEDROCORE_FECHAMENTO_DOCUMENTAL_FINAL_ERAS_1_A_3]].

```text
ERA 1 — PASS
Operational Intelligence Foundation

ERA 2 — PASS
Motor de Risco de Execução por IA

ERA 3 — FOUNDATION PASS / TRAINING DEFERRED
```

- Operational Learning está implementado com reports, outcomes, Operational
  Memory, Retrieval V1 e Safe Reuse; ele não altera pesos neurais.
- Risk Engine está implementado como subsistema analítico/governante, com blast
  radius, analytical dry-run, contratos assinados, gates, pós-execução e
  histórico; ele não executa a operação alvo e não substitui QA.
- Candidate Acquisition Foundation está implementada com seleção explícita,
  privacy, provenance, autorização purpose-bound, Candidate Store e readiness.
- Candidatos reais autorizados: **0**; readiness: **`DATASET_NOT_READY`**.
- Canonical Dataset, splits, Hugging Face, fine-tuning, modelo próprio e Local
  Provider treinado: **não iniciados ou inexistentes**, conforme o caso.
- Evidência backend mais recente disponível: `924 passed, 7 skipped, 2 warnings`;
  Ruff global PASS; Pyright Era 3 sem erros. O número `911` do briefing foi
  superado pelo checkpoint posterior no mesmo HEAD.

Dívida preservada: warnings de depreciação, Strix bloqueado por pré-requisitos
locais, resíduos humanos preexistentes no frontend e whitespace preexistente em
`global.css`.

## PEDROCORE-V1-FINAL-CLOSURE — PASS COM RESSALVAS (CHECKPOINT HISTORICO)

Checkpoint de produto preservado. Mapa: [[MOC_UX_V1]]. Relatório:
[[20-ux-v1/PEDROCORE_V1_FINAL_CLOSURE_01]].

### Produto

O Veltrix é o **gateway/orquestrador central de IA** do ecossistema Pedro.
Sistemas consumidores (FinGuard, Structa e futuros) e o próprio frontend enviam
mensagem, contexto e tipo de tarefa; o Veltrix resolve identidade,
autorização, provider, modelo e prompt, e devolve resposta padronizada.

### Estado

**Operacional e homologado para uso local e para o ecossistema local.** Sem
dívida arquitetural bloqueante. Naquele checkpoint, a publicação no GitHub
estava liberada tecnicamente; ela foi concluída em 03/09/2026. Exposição da API
na internet continua **não** suportada.

### Frontend

Interface pública fechada na versão de produto **V5.2.0**:

- composer único com textarea, seletor de IA, anexos e microfone;
- Configurações em drawer acessível (Escape, foco, `aria-modal`);
- sem cards de provider no topo, sem painel lateral direito permanente;
- autorização de provider real persistida por **ID** e sobrevivendo ao F5;
- modo DEV coerente: `mock` é destino real de conversa, com selo `DEV`;
- ditado por voz sem gravar nem transmitir áudio;
- anexos textuais reais pelo contrato `artifacts` já existente;
- seletor de IA agrupado ao botão Enviar, listando as cinco IAs públicas com
  estado real (indisponíveis visíveis e desabilitadas);
- **117 testes** frontend, os primeiros do projeto.

Ver [[20-ux-v1/UX_COMPOSER_V1]], [[20-ux-v1/VOZ_E_ANEXOS]] e
[[20-ux-v1/PROVIDERS_MODO_DEV]].

### Backend

**Inalterado nesta frente.** Nenhum arquivo de `apps/api/` foi modificado.
Versão técnica permanece `0.2.0`. Todos os contratos congelados foram
preservados: `/api/chat`, `/api/orchestrate`, FinGuard, `ChatRequest`, registry,
`provider=auto`, caller policies, binding, safe mode, fallback e circuit
breaker.

### Provider real

**Gemini** (`gemini-3.5-flash`) é a única IA pública **habilitada/homologada**
para uso real e autorizada para `auto`.

OpenAI, Claude, DeepSeek e Grok/xAI continuam **catalogadas e visíveis** na
interface — Configurações e seletor — porém indisponíveis até configuração e
homologação. Aparecem com estado factual (`Não configurado` / `Não homologado`)
e desabilitadas, nunca escondidas.

Três estados distintos, que não devem ser confundidos: **visível** (IA conhecida),
**configurado** (backend tem credencial) e **selecionável** (pode conversar
agora). Ver [[20-ux-v1/PROVIDERS_MODO_DEV]].

### Providers internos

`mock` fallback seguro e único destino de conversa em desenvolvimento;
`local_qa` análise determinística de artefatos; `local_model` opt-in default-off
sem transport real; `auto` estratégia de roteamento. Nenhum deles é apresentado
como IA pública.

### Integrações

FinGuard homologado 4/4 (evidência preservada). Structa registrado como consumer
de menor privilégio. Ambos **intocados** por esta frente.

### Segurança

Seguro para uso local (A), ecossistema local (B) e código público no GitHub (C).
**Não seguro** para API pública na internet (D) — faltam autenticação
obrigatória no `/api/chat`, rate limiting, teto de payload e TLS. Ver
[[20-ux-v1/MODELO_DE_AMEACA]].

### Testes — números REAIS desta execução

```text
backend    751 passed, 7 skipped, 2 warnings
frontend   117 passed (6 arquivos)
typecheck   PASS
build       PASS
docs graph  138 documentos, zero órfãos, zero links quebrados
```

### Multimodal

Imagem, PDF e DOCX **adiados formalmente para a V2**, por exigirem mudança na
assinatura de `BaseAIProvider.generate_response`, que hoje só carrega texto.
Ver [[20-ux-v1/V2_MULTIMODAL]].

### Ressalva daquele veredito — superada

Naquele checkpoint, `LICENSE` ainda não existia e dependia de decisão humana.
A pendência foi superada: o repositório público contém a Apache License 2.0 e
as metadatas dos dois pacotes usam `Apache-2.0`.

## PEDROCORE-STRUCTA-CONSUMER-01 — PASS (HISTÓRICO)

> Superada pela seção acima quanto a frontend, testes e status. A parte de
> identidade, autorização e onboarding do Structa permanece vigente.

O Structa foi registrado como consumer externo read-only de menor privilégio:
`project_id=structa`, identidade `registered`, papel `technical_tool`, task
única `qa_report_analysis` e autorização somente para Gemini em ambiente não
produtivo. Safe mode e fallback real continuam default-off. Consumers,
providers, roles e tasks fora da matriz permanecem negados.

Validação: 66 testes focados; suite integral com `751 passed, 7 skipped, 2
warnings`; Ruff focado e build web PASS; zero rede/provider real. Gate:
[[17-multi-provider-safe-evolution/GATE_PEDROCORE_STRUCTA_CONSUMER_01]]. A
Etapa 13 do Structa não foi iniciada.

## Reorganização documental canônica — 2026-08-02

O vault canônico passou de `docs/` para `Veltrix/`, preservando com hash
e correspondência de conteúdo os 127/127 documentos rastreados anteriores.
Naquele checkpoint, o [[MANIFESTO_REORGANIZACAO_20260802]] registrou 128 documentos
e 697 links resolvidos, sem órfãos, links quebrados, ambiguidades, basenames
duplicados ou becos sem saída. O teste direcionado concluiu com
`15 passed, 1 warning` e o validador canônico também saiu com código zero.

Esta reconciliação alterou somente a raiz documental e seu validador. Não
reabriu providers, orquestração, políticas, frontend nem homologações reais.

## ENCERRAMENTO FINAL — CHECKPOINT CANÔNICO HISTÓRICO

`FINGUARD-PEDROCORE-CANONICAL-REPLAY-DOCS-GRAPH-FINALIZE-01` —
[[19-encerramento-final/PEDROCORE_ENCERRAMENTO_FINAL_01]].

```text
PEDROCORE ENCERRADO — CORE OPERACIONAL CONCLUÍDO
```

```text
Dívidas      aprovado   (evidência real anterior)
Economizar   aprovado   (evidência real anterior)
Crescer      aprovado   (evidência real anterior)
Organizar    aprovado   (evidência real NOVA, desta frente)
```

**Homologação real consolidada: 4/4.**

O cenário Organizar — última limitação aberta — foi aprovado com Gemini real:
`provider_effective=gemini`, `model=gemini-3.5-flash`, `fallback=false`,
`retry=0`, exatamente **um** dispatch externo, `23.049 ms`, resíduo zero.

A causa da falha anterior deixou de ser um ponto cego: o replay canônico do
FinGuard passou a **persistir o diagnóstico em disco antes do teardown**, em vez
de apenas imprimi-lo num processo prestes a morrer.

Suíte integral após todas as alterações: `736 passed, 7 skipped, 2 warnings`;
eval `14/14`, `risk_level="none"`. Grafo documental daquele checkpoint íntegro (128
documentos, 697 links resolvidos, zero órfãos).

Arquitetura multi-provider: concluída. Multi-provider automático operacional:
não — somente `gemini + gemini-3.5-flash` está homologado e elegível. Isso é
decisão de homologação, não pendência.

## Assistente IA — 3/4 (HISTÓRICO)

> **Superado pela seção acima.** Esta seção descreve o estado anterior à
> execução real do Organizar e é preservada como evidência.

`FINGUARD-PEDROCORE-ASSISTANT-FINAL-CLOSE-01` —
[[18-provider-output-budget-cancellation/PEDROCORE_ASSISTANT_FINAL_CLOSURE_01]].

```text
ASSISTENTE IA ENCERRADO COM LIMITAÇÃO EXTERNA DOCUMENTADA — HOMOLOGAÇÃO REAL 3/4
```

A homologação real do Organizar consumiu o único dispatch autorizado daquela
frente e terminou em fallback seguro (`provider_used=mock`,
`duration_ms=3523`). A causa no lado do provider não pôde ser determinada — a
observabilidade é um ring buffer em memória e foi perdida no teardown — e a
assinatura diferia da histórica (~30 s/~60 s). Um diagnóstico estrutural local
comprovou que o adapter async, o orçamento e o timeout de transporte funcionam;
**nenhum defeito local objetivo foi demonstrado**, então não houve repetição
nem nova implementação naquela frente.

Checkpoint documental anterior: [[17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7]] e [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]] consolidam as Etapas 1–7.

Nenhuma implementação obrigatória permanece no Assistente IA.

## Frente anterior

`PEDROCORE-PROVIDER-OUTPUT-BUDGET-CANCELLATION-01` —
[[18-provider-output-budget-cancellation/FECHAMENTO_PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]].

O adapter Gemini passou a ter orçamento explícito de saída
(`min(global_cap, model_cap, task_cap)`), timeout de transporte derivado e
sempre menor que a espera da orquestração, cliente assíncrono nativo sem
`asyncio.to_thread`, lifecycle explícito, detecção de truncamento por
`finish_reason` e coleta real de `usage_metadata`. Validação:
`703 passed, 7 skipped`, eval `14/14`, zero chamadas externas reais.

Estado honesto do cancelamento: a task, o `await` e o transporte local são
cancelados de verdade; **a geração remota não é comprovadamente interrompida**.
Por isso `completion_ambiguous` foi preservado e timeout continua sem disparar
retry, segundo provider ou fallback real.

Estado da homologação FinGuard:

```text
Assistente operacional     sim
Gemini real                comprovado anteriormente
cenários homologados       3/4 (Dívidas, Economizar, Crescer)
Organizar                  pendente por variabilidade/timeout
```

O Organizar **não foi revalidado** nesta frente: nenhuma chamada real foi
feita. O orçamento de saída reduz risco, mas não prova a causa dos timeouts
históricos de ~30 s e ~60 s.

## Status oficial

Projeto finalizado como core operacional seguro. No histórico público
sanitizado, `v7.0.0` aponta para
`6c4757a79ccb0b032eb860647efb1d345815d3b8` e `v6.0.0`, marco do MVP backend,
aponta para `502acb8ee02ac6a7c007c823b73a1ad745836118`. Este é o documento de status
oficial do projeto; prevalece sobre qualquer status histórico/duplicado ainda
presente em `Veltrix/`.

DOCFIX anterior: `Veltrix/00_MAPEAMENTO_GERAL_PEDROCORE.md` e os MOCs Obsidian em `Veltrix/MOC_*.md` organizam a leitura atual sem alterar código funcional.

Frente mais recente: Etapa 7 de
`PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION`. O fallback real controlado existe
somente para falha `provider_pre_dispatch` com prova de `not_dispatched`; é
interno, default-off, limitado a `assistant_chat`/`ecosystem_assistant`, um
secundário distinto e dois registros de tentativa. Timeout continua como
conclusão ambígua e nunca dispara secundário. Como apenas
`gemini + gemini-3.5-flash` está homologado/autorizado no catálogo real, o
fallback multi-provider operacional permanece indisponível. Validação final é
`570 passed, 7 skipped, 2 warnings`, eval `14/14`, Ruff aprovado e zero
chamadas externas reais.

Correção anterior concluída:
`PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION — Fix — homologação e configuração
de modelos`, commit `8c97004`. `_MODEL_CATALOG` passou a ser a fonte explícita
dos modelos reconhecidos; configuração runtime apenas escolhe um identificador
e não cria/homologa entrada. Provider/model binding agora é total e falha
fechado antes de qualquer adapter real. Validação final registrada:
`515 passed, 7 skipped`, eval harness `14/14`, zero chamadas reais e
Gemini-only preservado.

### Estado consolidado da evolução multi-provider

| Etapa | Estado |
| --- | --- |
| Etapa 1 — catálogo de providers/modelos | concluída |
| Etapa 2 — identidade e autorização por projeto | concluída e corrigida |
| Etapa 3 — provider/model binding | concluída e corrigida |
| Etapa 4 — política determinística em shadow mode | concluída |
| Etapa 5 — roteamento enforced com chamada única | motor concluído; diversificação bloqueada por homologação |
| Etapa 6 — health/circuit breaker | concluída localmente; default-off e por processo |
| Etapa 7 — fallback real controlado | mecanismo pre-dispatch concluído; default-off e sem segundo homologado |

| Capacidade | Veredito atual |
| --- | --- |
| Multi-provider estrutural | sim |
| Identidade e autorização por projeto | sim |
| Provider/model binding total | sim |
| Shadow mode | sim |
| Multi-provider automático real | não |
| Health/circuit breaker | sim, local/default-off |
| Fallback entre providers reais | mecanismo pre-dispatch sim; operacional não |

O único candidato automático real permanece Gemini. Claude e OpenAI não são
executados automaticamente. Sem binding válido, `provider=auto` faz zero
chamadas reais e usa o Mock seguro; seleção técnica explícita é bloqueada com
zero adapters.

Frente anterior concluída: `PEDROCORE-OBSERVABILIDADE-LOCAL-01` — ring buffer sanitizado e default-off, painel `#/observability`, provider/fallback/timeline, relatórios, memória técnica, avaliação e release gate instrumentados no pipeline real. Integração local FinGuard → Veltrix → FinGuard e replay conjunto aprovados. Commits `b22338a`, `df6d72f`, `f995d5e`, `3b11b36`. Pytest: `368 passed, 7 skipped, 2 warnings`; frontend build verde. Gemini real não foi executado nesta frente porque os dois opt-ins permaneceram desligados. Ver `Veltrix/13-fechamento/FECHAMENTO_PEDROCORE_OBSERVABILIDADE_LOCAL_01.md`.

Frente anterior: `PEDROCORE-MODEL-FOUNDATION-01` — fundação de inteligência própria, commitada em `689e50a`. Ver `Veltrix/13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01.md`.

Ultima frente de implementacao: `PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01` — pacote (A) contrato de ecossistema, (B) memória técnica controlada, (C) `local_model` opt-in sem rede, (D) eval harness determinístico; implementada de forma retrocompatível e commitada em `e0ff8e3`. O Veltrix continua **não** sendo modelo treinado: sem fine-tuning, sem autoaprendizado, sem RAG, sem provider real. Testes: `296 passed, 6 skipped, 2 warnings`. Ver `Veltrix/13-fechamento/FECHAMENTO_PEDROCORE_ECOSYSTEM_INTELLIGENCE_SUITE_01.md`.

Ultima frente commitada: `PEDROCORE-QA-SAFETY-HARDENING-01` — endurecimento de QA/safety sem reabrir o core funcional, commitada em `d6106b7`. Pytest: `341 passed, 6 skipped, 2 warnings`. Eval harness: `14/14 passed`, `risk_level="none"`. Provider real e rede real nao foram chamados em testes; Report Memory continua default-off e nao e treinamento; `local_model` real ficou fora de escopo; FinGuard e `qa:finalize:02` ficaram intocados. Ver `Veltrix/16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01.md`.

Frente documental anterior concluída: `PEDROCORE-DOCS-GRAPH-LINKING-01` — organização de links Markdown/Obsidian na raiz `docs/` da época, hoje `Veltrix/`, sem alteração de código.

Frente local **validada com sucesso**: `FINGUARD-PEDROCORE-ASSISTANT-REAL-PROVIDER-QA-01`. O Veltrix decide `provider=auto` para consumidores externos: mock default, `local_qa` preservado, Gemini real somente com `allow_real_provider=true` e `GEMINI_API_KEY` no ambiente Veltrix. Corrigido bug de fallback que vazava texto tecnico/debug (`MockProvider`, `mock-v1`, erro bruto) na resposta conversacional — fallback agora sempre seguro/conservador (ver `Veltrix/08_CHANGELOG.md`). Validacao manual confirmou Gemini real respondendo de forma conversacional via `provider=auto` (modelo `gemini-2.5-flash`; `gemini-3.5-flash`, o default de `.env`, estava com 503 transitorio do lado do Google no momento do teste). Teste real Gemini fica manual/opt-in e skipado por padrao. Pytest: `351 passed, 7 skipped, 2 warnings`.

## Versão atual de produto

**V5.2.0** (era V5.1.9 até 14/08/2026). Minor da linha 5.x: a frente
`PEDROCORE-V1-FINAL-CLOSURE` acrescentou recursos de interface — composer,
drawer, voz e anexos — sem quebrar contrato de API. A versão técnica do backend
permanece `0.2.0`. Ver [[MOC_VERSOES_STATUS]].

## Frente anterior

Projeto **finalizado localmente** como core operacional seguro (`v7.0.0`). Últimas frentes: `PEDROCORE-IMPLEMENT-04` (Blocos 8–11, `18d1fc5`), `PEDROCORE-IMPLEMENT-05` (05A–05F: flags/guards opt-in, FinGuard controlado com policy forte, reader consolidado, OCR/multimodal/Playwright como opt-in seguro) e `PEDROCORE-FINALIZE-06` (06A enforcement final do release gate + 06B fechamento). A tag `v6.0.0` (MVP backend) permanece intocada em `ee2ac68`. Ver `Veltrix/13-fechamento/FECHAMENTO_PEDROCORE_FINAL.md`.

`PEDROCORE-REPLAN-01` (01A a 01E) está **concluída no escopo documental** e commitada:

- `1e5a8cb — docs: iniciar PEDROCORE-REPLAN-01A`
- `6e7badd — docs: planejar contratos PEDROCORE-REPLAN-01B`
- `c1e7816 — docs: definir arquitetura-alvo PEDROCORE-REPLAN-01C`
- `8c68b67 — docs: planejar QA Intelligence PEDROCORE-REPLAN-01D`
- `cc808a7 — docs: fechar PEDROCORE-REPLAN-01E`

Implementação inicial de código:

- `PEDROCORE-IMPLEMENT-01A/01B` (Task Router mínimo + metadados de resposta) commitada em `577bc88`; correção documental commitada em `20e6cff`.
- `PEDROCORE-IMPLEMENT-01C/01D/01E/01F/01G/01H` (Project Context, Prompt Builder, metadados estruturais, audit não persistente) commitada em `95cbfab`; correção documental commitada em `1ff1758`.
- `PEDROCORE-IMPLEMENT-02A/02B/02C/02D/02E/02F/02G` — Policy de `allowed_tasks`, artefatos textuais por payload, Prompt Builder com artefatos, QA response skeleton seguro, warnings específicos de QA textual e testes de contrato — implementada, validada e commitada em `e115672`. Testes backend: `66 passed, 2 warnings`. `apps/web` limpo, `.env` intocado, nenhum provider real chamado, FinGuard não acessado, nenhum endpoint novo criado, QA skeleton sem análise real, `can_advance` nunca `true`.

## Layout do repositorio

```txt
veltrix/
  apps/api/
  apps/web/
  Veltrix/
```

## Concluído

- Backend FastAPI com estrutura multi-provider (`BaseAIProvider`, `ProviderRegistry`, 6 providers: Mock, Gemini, OpenAI, Claude, DeepSeek, Grok).
- Endpoints `/`, `/health`, `POST /api/chat`, `GET /api/providers`, `POST /api/orchestrate`.
- Fallback automático para `MockProvider` quando um provider real falha ou não está configurado.
- Frontend React/Vite/TypeScript com histórico local (`localStorage`), feedback gostei/não gostei, painel de configuração de providers e identidade visual aplicada (V5.1.9).
- Testes de backend cobrindo chat mock, fallback por provider desconhecido, validação de payload e listagem de providers.
- `PEDROCORE-REPLAN-01A` — visão oficial, objetivo, roadmap, status, decisões técnicas e changelog reformulados (commit `1e5a8cb`).
- `PEDROCORE-REPLAN-01B` — contratos técnicos planejados (`Veltrix/10-contratos/`): contrato de orquestração, tipos de tarefa, resposta estruturada, contrato de artefatos, provider preference, fallback e relação com QA Intelligence (commit `6e7badd`).
- `PEDROCORE-REPLAN-01C` — arquitetura-alvo documentada (`Veltrix/11-arquitetura-alvo/`): Task Router, Prompt Builder, Project Context, Provider Orchestration, Structured Responses, Artifact Reader, Audit/logs, relação com `/api/chat` e com o FinGuard (commit `c1e7816`).
- `PEDROCORE-REPLAN-01D` — planejamento de QA Intelligence documentado em `Veltrix/12-qa-intelligence/` (definição, relação com o QA Automation do FinGuard, artefatos analisáveis, relatórios Markdown, casos de uso, resposta estruturada, severidade/risco, regra de avanço/bloqueio, fallback Mock, análise visual futura e limites/proibições) (commit `8c68b67`).
- `PEDROCORE-REPLAN-01E` — fechamento documental da reformulação, consolidado em `Veltrix/13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01.md` (commit `cc808a7`).
- `PEDROCORE-IMPLEMENT-01A/01B` — Task Router mínimo implementado em código: `task_type`, `origin_system`, `context` e `metadata` opcionais no `ChatRequest`; Task Router mínimo em `apps/api/app/modules/task_router/` reconhecendo 7 task_types + `unknown`, sem bloqueio duro; metadados de tarefa (`task_type`, `origin_system`, `task_criticality`, `requires_structured_response`, `task_warnings`) no `ChatResponse`; warning forte quando fallback Mock ocorre em tarefa crítica. Commitada em `577bc88`.
- `PEDROCORE-IMPLEMENT-01C/01D/01E/01F/01G/01H` — Project Context mínimo (`apps/api/app/modules/project_context/`, resolve `pedrocore`/`finguard`/`unknown`, somente configuração interna); Prompt Builder mínimo (`apps/api/app/modules/prompt_builder/`, monta `enriched_system_prompt` sem chamar provider); metadados estruturais novos no `ChatResponse` (`project_id`, `project_read_only`, `project_can_execute_commands`, `project_can_write_files`, `response_style`, `audit_id`, `audit_timestamp`); audit metadata não persistente (`apps/api/app/modules/audit/`, `audit_id`/`timestamp` gerados em memória, sem banco/arquivo/log); testes backend: `37 passed, 2 warnings`. Commitada em `95cbfab`.
- `PEDROCORE-IMPLEMENT-02A/02B/02C/02D/02E/02F/02G` — QA textual foundation: policy de `allowed_tasks` (`ChatResponse.task_allowed_for_project`), artefatos textuais por payload (`apps/api/app/modules/artifacts/`, `ChatRequest.artifacts`, `ChatResponse.artifact_count`/`artifact_types`/`artifact_warnings`), Prompt Builder com seção `[Artefatos enviados]`, QA response skeleton seguro (`apps/api/app/modules/qa_response/`, `ChatResponse.qa_skeleton`, sempre `status="not_analyzed"`/`can_advance=False`/`confidence=0.0`, sem análise real), warnings específicos de QA textual e testes de contrato. Testes backend: `66 passed, 2 warnings`. Commitada em `e115672`.
- `PEDROCORE-IMPLEMENT-03` — MVP backend (Blocos 1–7): QA textual real inicial (heurística local determinística em `apps/api/app/modules/qa_analysis/`, skeleton preenchido com `analysis_source="local_text_heuristic"`), release gate conservador (`evaluate_release_gate` com `blocked_reason`), `POST /api/orchestrate` (pipeline centralizado em `apps/api/app/modules/orchestration/`, consumido também pelo `/api/chat`), safe mode (`allow_real_provider=false` por padrão, `PROVIDER_REAL_BLOCKED`), autenticação interna opcional (`PEDROCORE_INTERNAL_API_KEY` + `X-Veltrix-Api-Key`, somente `/api/orchestrate`), warning/error contract padronizado (`apps/api/app/modules/contracts/`) e audit não persistente completo (`latency_ms`, `provider_used`, `safe_mode_blocked`, `risk_level`, `can_advance`). Limites de artifacts (10 / 20k / 100k) e rejeição de campos de path sem leitura de disco. Testes backend: `125 passed, 2 warnings`. Commitada em `6ed4c41`.
- `PEDROCORE-FINALIZE-04` — consolidação documental do MVP backend, exemplos de API e preparação/registro da tag. Commitada em `ee2ac68`; tag anotada `v6.0.0` criada com a mensagem `v6.0.0 - MVP backend Veltrix`, apontando para `ee2ac68`.
- `PEDROCORE-IMPLEMENT-04` — expansão operacional segura (Blocos 8–11): contrato FinGuard por payload fake, Artifact Reader controlado, QA visual stub, agente exploratório assistido. Commitada em `18d1fc5`.
- `PEDROCORE-IMPLEMENT-05` — flags/guards/testes opt-in, FinGuard controlado com policy enforcement forte, reader consolidado, OCR local opt-in, multimodal guard e Playwright read-only opt-in. Commitada nas subfrentes `33a7dc2`, `790e1b4`, `70afba1`, `b3f1be5`, `2670040`, `3bcfa05`.
- `PEDROCORE-FINALIZE-06` — enforcement final do release gate, documentação
  final e tag anotada `v7.0.0`. Após a sanitização do histórico para publicação,
  a tag pública aponta para `6c4757a79ccb0b032eb860647efb1d345815d3b8`.

- `PEDROCORE-MODEL-FOUNDATION-01` — fundação de inteligência própria: Intelligence Layer (`intelligence_layer/`, plano determinístico interno por task, nunca habilita provider real), Report Intelligence Foundation (`report_intelligence/`, sinais determinísticos de relatórios técnicos, sem persistência), contrato futuro do Local Model Provider (`providers/local_model_contract.py`, `local_model` ≠ `local_qa`, sem geração), Evaluation Foundation (`evaluation/`, checks de segurança/coerência) e 4 task_types novos somente para `pedrocore`. Testes backend: `257 passed, 6 skipped, 2 warnings` (41 novos). Commitada em `689e50a`.

- `PEDROCORE-ECOSYSTEM-INTELLIGENCE-SUITE-01` — inteligência de ecossistema: contrato para consumidores + tasks de assistente (disclaimer obrigatório em `finance_advice`), memória técnica controlada (`report_memory/`, rotas `/api/reports/*` e `/api/project-memory/*`, default off, `context_from_memory` opt-in), provider `local_model` opt-in default-off (sem rede nesta frente; nunca aprova release gate) e eval harness determinístico (`eval_harness/`, 11 fixtures). Testes: `296 passed, 6 skipped, 2 warnings` (39 novos). Commitada em `e0ff8e3`.

- `PEDROCORE-QA-SAFETY-HARDENING-01` — guard estrutural contra provider real em testes, suites de safety para provider real/Report Memory/policy/contrato `/api/orchestrate`, eval harness estendido para 14 casos e docs de release gate em `Veltrix/16-qa-safety-hardening/`. Testes: `341 passed, 6 skipped, 2 warnings`; eval harness `14/14 passed`, `risk_level="none"`. Commitada em `d6106b7`.

## Em andamento

Sem frente interna bloqueante aberta após `PEDROCORE-OBSERVABILIDADE-LOCAL-01`.
Trabalhos futuros — homologação de outro provider real, transport real do
`local_model`, persistência operacional da observabilidade, deploy e execução
real de OCR/multimodal/Playwright — são opcionais ou externos e exigem nova
aprovação. A publicação do código no GitHub já foi concluída.

## Ainda não existe / permanece opcional

- Persistência operacional da observabilidade — o store atual é um ring buffer local/volátil e intencionalmente default-off.
- QA Intelligence com IA real — a análise QA atual é heurística textual local determinística (`local_text_heuristic`); não usa provider real, não substitui validação humana e não executa testes.
- Execução de comandos pelo Veltrix — `suggested_commands` são apenas strings seguras, nada é executado; o agente exploratório é assistido (plano/manual) e nunca executa ações.
- QA visual real multimodal — artefatos visuais geram stub conservador; OCR e Playwright existem como recursos opt-in/controlados, não como teste padrão nem release gate automático.
- Provider real liberado em fluxo crítico — safe mode bloqueia por padrão; liberação exige `allow_real_provider=true` explícito e ainda assim provider real nunca aprova release gate sozinho.
- Otimização dinâmica de provider por custo/qualidade/task; o roteamento determinístico shadow/enforced já existe.
- Memória técnica persistente por default e RAG — `report_memory` existe com persistência default off e modos opt-in (`memory`/`local_json`); RAG/embeddings ainda não existem.
- Provider generativo local funcional — `local_model` está registrado como provider opt-in default-off, mas sem transport real; nenhum backend (Ollama/llama.cpp/LM Studio) foi instalado ou chamado.
- Treinamento, fine-tuning ou autoaprendizado — fora do escopo do projeto; a fundação de inteligência é determinística e avaliada (`evaluation/`).
- Persistência de audit e observabilidade em banco/log (ambos permanecem
  voláteis). Dashboard público/admin (Bloco 12): **cancelado por decisão de
  produto**, não é pendência; o painel técnico local/QA foi implementado em
  `#/observability`.
- Análise multimodal (imagem, PDF, DOCX) — adiada formalmente para a V2 em [[20-ux-v1/V2_MULTIMODAL]].

## Proibido nesta fase

> **Atualizado em 16/08/2026.** A proibição anterior de alterar `apps/web` valia
> para as frentes de backend/QA e foi **levantada** por
> `PEDROCORE-V1-FINAL-CLOSURE`, cujo escopo era exatamente fechar o frontend.
> O backend é que permaneceu intocado nessa frente. A lista abaixo reflete as
> restrições vigentes.

- Chamar providers reais (Gemini, OpenAI, Claude, DeepSeek, Grok) sem
  autorização humana explícita — inclusive em testes.
- Alterar `.env` real ou versionar qualquer credencial.
- Ler, escrever ou executar comandos no repositório do FinGuard ou do Structa.
- Leitura de arquivo fora do Artifact Reader allowlisted (que permanece desabilitado por padrão e proibido para FinGuard).
- Implementar execução de comandos recebidos por payload.
- Remover documentação histórica; ela é preservada e identificada como histórica.
- Criar, mover, deletar ou recriar tag.
- Expor a API à internet sem os requisitos de [[20-ux-v1/MODELO_DE_AMEACA]].

## Riscos atuais

- **Documentação histórica duplicada:** ainda existem pares em `Veltrix/` (ex.: `03_ROADMAP.md` vs `03-versoes/ROADMAP.md`, `09-status/STATUS_ATUAL.md` desatualizado). Foram preservados por prudência; o status canônico é este arquivo.
- **Provider real autorizado explicitamente:** qualquer execução manual com provider real, chave/configuração disponível e `allow_real_provider=true` pode gerar chamada externa/custo. Testes padrão devem usar `mock` ou `local_qa`.
- **Fallback Mock — semântica por boundary (corrigida no Final Functional Gate):**
  o comportamento deixou de ser único.
  *Consumers integrados* (FinGuard, Elyra, Structa e demais) mantêm o contrato
  original: `allow_mock_fallback` continua `true` por padrão e o fallback seguro
  segue existindo para não deixar o consumidor sem resposta — o consumidor
  continua responsável por checar `fallback_used` (ver Decisão Técnica 014).
  *Chat interativo do próprio Veltrix*, quando o usuário escolhe explicitamente
  uma IA real: a requisição envia `allow_mock_fallback=false`, e uma falha do
  provider volta como falha (`provider="none"`, `fallback_used=false`,
  `status="blocked"`), com a interface nomeando qual IA falhou. Uma resposta do
  Mock não é mais apresentada como se fosse da IA selecionada.
- **Structured response parcial:** `/api/orchestrate` já retorna `qa`, `release_gate`, `visual_qa_analysis`, `exploration`, `warnings` e `audit`, mas `answer` continua texto livre; otimização dinâmica por custo/qualidade/task ainda não existe.

## Próximos passos opcionais

- Deploy público, somente depois dos requisitos de
  [[20-ux-v1/MODELO_DE_AMEACA]].
- Execução real de OCR, QA visual multimodal e Playwright somente com flags, dependências instaladas manualmente e revisão humana.
- Homologar um segundo provider/modelo real em frente separada, escolhendo Claude ou OpenAI explicitamente; fluxo crítico continua exigindo autorização e revisão específica.
- Saneamento adicional de documentação histórica/duplicada dentro de `Veltrix/`, se o usuário quiser reduzir ruído do vault.
