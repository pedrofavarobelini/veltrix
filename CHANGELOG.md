# Changelog

Mudanças relevantes do Veltrix.

O histórico detalhado por versão de produto (V1 a V5.1.9) está em
`Veltrix/08_CHANGELOG.md` e permanece a fonte para aquele período.
Este arquivo começa no programa **AI Runtime & Learning Control Plane**.

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

---

## Reconciliação documental final — 03/09/2026

Frente **exclusivamente documental**. Zero alteração em código, migrations,
contratos, versão de produto, versão de API ou tags.

Uma auditoria read-only do vault concluiu `DOCUMENTATION STATE =
CURRENT_WITH_DRIFT` e `STUDY PACK = STALE`: o grafo estava íntegro (zero órfãos,
zero links quebrados), mas o Final Functional Gate existia em apenas quatro
documentos e a pasta de estudos estava congelada em 09/07/2026 — dois meses e
quinze subsistemas atrás.

### Corrigido

- **Hierarquia de fechamentos.** `MOC_FECHAMENTOS` apontava
  `PEDROCORE_ENCERRAMENTO_FINAL_01` como "CANÔNICO ATUAL"; o canônico passou a
  ser o Final Functional Gate, e o anterior foi rotulado como fechamento
  histórico. Nenhum fechamento foi removido.
- **Rótulos "atual" incorretos.** `MOC_VERSOES_STATUS` chamava o checkpoint de
  20/08 de atual; `MOC_TESTES` tinha quatro seções "Resultado atual" com datas
  diferentes. Ambos ganharam uma seção corrente real e os antigos viraram
  `SNAPSHOT DO CHECKPOINT`.
- **`09_STATUS_ATUAL`** ganhou o estado corrente no topo e deixou de descrever o
  projeto como em "manutenção" — está congelado.
- **Fallback Mock silencioso** deixou de ser listado como risco presente sem
  qualificação: o texto passou a distinguir consumers integrados (contrato
  original, `allow_mock_fallback=true`) do chat interativo (`false`, falha não
  disfarçada).
- **`VELTRIX_FINAL_STATE`** chamava UX + Project Registry de "última frente
  funcional"; ganhou a seção 12 com o Final Functional Gate, provider truth,
  correções de UX, homologação humana e freeze.
- **Roadmap.** Duas entradas diziam "commit pendente de autorização" para
  frentes commitadas em `689e50a` e `e0ff8e3`; viraram `DONE`. O
  `03_ROADMAP.md` original foi rotulado `HISTÓRICO / SUPERSEDED`.
- **`README`** passou a declarar o freeze, a semântica do fallback por boundary
  e o fechamento canônico.
- **Roteiro NotebookLM**: as 14 fontes apontavam para a árvore `docs/`, que não
  existe desde 02/08/2026. Substituídas por 19 fontes do vault atual,
  verificadas uma a uma.

### Adicionado

- `HUMAN_RUNTIME_ACCEPTANCE = PASS` (03/09/2026) registrado no Final Functional
  Gate, no status, nos MOCs e no study pack — com a distinção explícita entre
  aceite **visual** (aparência) e aceite em **runtime** (fluxo real em uso).
- `Veltrix/15-estudo-pedrocore/VELTRIX_RISK_ENGINE_ESTUDO.md` — o maior
  subsistema em forma didática: pipeline, P1–P5, Console, Project Registry.
- `Veltrix/15-estudo-pedrocore/VELTRIX_LINHA_DO_TEMPO.md` — como um chat com
  providers virou um control plane, em doze fases comprovadas pelo Git.
- Navegação direta no `MOC_VELTRIX` para Risk Engine V2, Risk Console, Project
  Registry, Control Plane, Universal Contracts e Platform Evolution.

### Alterado

- **Study pack reconciliado** (resumo executivo, mapa mental, fluxo completo,
  glossário, perguntas e respostas, flashcards, roteiros): passou a ensinar o
  Veltrix que existe hoje — dois planos, Risk Engine, Control Plane, Evidence,
  os seis estados de provider, `DATASET_NOT_READY` sem exagero, o rename e o
  freeze.
- Os flashcards deixaram de memorizar `296 passed` e `e0ff8e3` como estado
  atual; números frágeis ficaram isolados e datados como checkpoint.
- `PEDROCORE_AUDITORIA_STUDY_MAP_01` rotulado **HISTÓRICO** e
  `PEDROCORE_VEREDITO_FINAL` rotulado **SUPERSEDED**, ambos com o conteúdo
  preservado sem alteração e apontando para o material atual.

Nenhum documento foi apagado. O objetivo não era limpar história — era impedir
que história pareça presente.

---

## Final Functional Gate — 03/09/2026

**VELTRIX FINALIZATION = PASS. VELTRIX FUNCTIONAL FREEZE = ACTIVE.**

Última frente de manutenção comum do Veltrix. Registro completo em
`Veltrix/19-encerramento-final/VELTRIX_FINAL_FUNCTIONAL_GATE.md`.

### Corrigido

- **Chat com provider real deixou de degradar em silêncio para o Mock.** Quando
  o usuário escolhe explicitamente uma IA real no chat do próprio Veltrix, a
  requisição passa a enviar `allow_mock_fallback: false` — opt-out restritivo
  que já existia em `ChatRequest`. Uma falha do Gemini volta como falha
  (`provider="none"`, `fallback_used=false`, `status="blocked"`), e a interface
  diz qual IA falhou em vez de exibir texto do Mock como se fosse a resposta.
  O default do contrato **não** mudou: FinGuard, Elyra e Structa seguem com o
  fallback seguro.
- **Disclaimer financeiro fora de contexto.** A resposta de fallback era única e
  afirmava "não executa nenhuma ação financeira nem altera seus dados" mesmo em
  perguntas sobre o sistema. `_fallback_answers()` passou a escolher a mensagem
  pelo contexto da requisição; FinGuard mantém o disclaimer.
- **Colisão nos cards de provider das Configurações.** O badge de status
  invadia nome e modelo. O card virou um grid por áreas, com o status em linha
  própria e uma coluna de cards no drawer. Verificado em Chrome headless de
  360 px a 1920 px: zero overlap e zero overflow horizontal.
- **"Observabilidade QA/local" sobrepondo o título "DIAGNÓSTICO LOCAL".** O link
  passou a ser `inline-flex` com espaçamento vertical real.

### Alterado

- Marcas de OpenAI e Claude redesenhadas: os assets anteriores eram glifos
  genéricos que não remetiam a nenhuma das duas. Continuam locais, sem CDN e
  sem dependência nova. Os cinco logos ganharam `display: block`,
  `object-fit: contain` e dimensão explícita.

### Adicionado

- `apps/api/tests/test_chat_provider_truth.py` — provider real sem
  consentimento não chega ao adapter; operador local autorizado alcança o
  Gemini; falha não é disfarçada de resposta; o default do contrato segue
  degradando para Mock; chat geral sem disclaimer financeiro; FinGuard com o
  seu; caller ambíguo sem privilégio.
- Cenários de verdade de provider na suíte do frontend, incluindo a pergunta
  simples da homologação.

---

## Polimento final do GitHub público — 03/09/2026

### Alterado

- O comando de instalação no `README.md` passou a usar diretamente
  `https://github.com/pedrofavarobelini/veltrix.git`.
- README, versionamento, status final e MOC foram reconciliados com o estado
  público: Apache-2.0 presente, `HUMAN_VISUAL_ACCEPTANCE = PASS`, Project
  Registry concluído e migrations `0001`–`0012`.
- Métricas de fechamentos anteriores passaram a ser identificadas como
  snapshots históricos, sem competir com a CI do HEAD corrente.
- Referências a publicação pendente e aos SHAs anteriores à sanitização do
  histórico foram substituídas pelo estado público verificável.

Nenhum código funcional, migration, tag ou Release foi alterado.

---

## Publicação pública — 03/09/2026

O repositório passou a ser público sob **Apache-2.0** em
`github.com/pedrofavarobelini/veltrix`. `HUMAN_VISUAL_ACCEPTANCE = PASS`.

Nenhuma mudança de comportamento do produto: contratos V1 congelados,
superfície HTTP e migrations intactos.

### Adicionado

- Guard de taxonomia de skips em `apps/api/tests/conftest.py`: a sessão falha
  se aparecer um skip fora das duas categorias declaradas (PostgreSQL de teste
  e opt-in de recurso real). A documentação prometia investigar skip novo; o
  guard passou a verificar isso em vez de prometer.

### Alterado

- `CONTRIBUTING.md` e `ci.yml` deixaram de afirmar uma contagem de skips e
  passaram a descrever as duas categorias. Contagem envelhece a cada teste
  novo — a taxonomia, não.
- `README.md` reorganizado: o que o Veltrix é vem antes do histórico de
  frentes, e as métricas de teste passaram a ser gates mais um snapshot
  datado, em vez de números antigos apresentados como resultado atual.
- Assets do frontend perderam o nome da marca antiga
  (`pedrocore-logo-icon.png` → `veltrix-logo-icon.png`). Os bytes da imagem
  não mudaram. Identificadores congelados (`PEDROCORE_*`,
  `pedrocore-integration/v1`, tabelas `pedrocore_*`) seguem preservados por
  compatibilidade.

### Removido

- Estado local do editor Obsidian (`Veltrix/.obsidian/`) e o script obsoleto
  `atualizar-docs-v1.ps1`, que gerava uma árvore `docs/` que não existe mais.
- Cópia duplicada e não referenciada do logo em `apps/web/public/`.

---

## UX final e Project Registry

O Risk Console passa a ter **três estados exclusivos** e o Veltrix ganha um
catálogo de projetos extensível.

```text
ENTRADA  →  REVISÃO DE CONTEXTO  →  RESULTADO
                                    gate → resumo → riscos → por quê →
                                    o que fazer → 6 abas de detalhe
```

### Adicionado

- **Project Registry** (`app/modules/project_registry/`): identidade de
  projeto com `Protocol` + InMemory + LocalJson + PostgreSQL, migration
  aditiva `0012`, seis projetos-semente e criação/edição/arquivamento pelo
  console. Identidade normalizada, única e imutável; arquivar nunca apaga.
- **NOVO PROJETO** e **GERENCIAR PROJETOS** no console.
- Visão primária do resultado: `RESUMO DA OPERAÇÃO`, `PRINCIPAIS RISCOS`,
  `POR QUÊ?` e `O QUE FAZER?`, com limite de cinco itens e ponteiro para o
  restante.
- `TabbedContent` com seis abas de detalhe, uma renderizada por vez.
- Atalhos `Ctrl+J` (avançar) e `Esc` (voltar). Nenhum atalho sugere executar.

### Alterado

- A lista de projetos passa a vir do Project Registry, e não do Capability
  Manifest. Um projeto **sem** manifesto é analisável; os fatos ausentes ficam
  `UNKNOWN`.
- A guarda de `build_request` deixa de exigir a capability `risk_analysis` e
  passa a exigir **projeto registrado e ativo** — guarda de identidade, não de
  capacidade.

### Não incluído, deliberadamente

- Sincronização com GitHub. `repository_url` é metadado; nenhuma rede é tocada,
  nenhum token é pedido.
- Qualquer alteração na decisão de risco. Teste de paridade compara gate,
  dimensões, alcance, cenários, achados e recomendações antes e depois.

---

## Risk Auto Context

Configurações Avançadas deixam de ser obrigatórias no fluxo diário. O prompt é
resolvido em uma **proposta de contexto** com origem e confiança por campo,
revisada por um humano antes da análise.

```text
PROMPT → polaridade → auto context → capabilities → executor → policy
       → PROPOSTA → revisão → CONFIRMAR → análise
```

- **Interseção de permissão**: pedida ∩ executor ∩ projeto ∩ política. Pedir
  `git.push` não concede push; capacidade negada vira conflito visível, e não
  entra na requisição.
- **`POLICY_DERIVED`** separado de `INFERRED`: política não é apresentada como
  declaração do usuário.
- **Confiança categórica** (`HIGH`/`MEDIUM`/`LOW`) — sem percentual decorativo.
- **Ambiguidade não vira escopo amplo**: sem alvo identificado, nenhuma
  permissão é proposta e o motor bloqueia.
- **Etapa de revisão** com `CONFIRMAR E ANALISAR`, `REVISAR DETALHES` e
  `CANCELAR`. Confirmar contexto **não** aprova execução.
- Perfis de executor e superfícies de projeto são **declarações**, não
  ramificações: projeto novo entra sem tocar em código.
- Caminho inteiramente determinístico; funciona sem IA.

## Veltrix — fechamento final

O produto passou a se chamar **Veltrix**. Estado completo em
`Veltrix/17-veltrix/VELTRIX_FINAL_STATE.md`; o que mudou de nome e o que foi
preservado em `Veltrix/17-veltrix/MIGRACAO_PEDROCORE_VELTRIX.md`.

### Durabilidade fechada

Model Registry, Asset Registry e Evaluation Plane ganharam persistência real
(migration `0011`, aditiva). Motivo concreto: promoção de modelo exige
evidência de avaliação — se a avaliação some no restart, o registry recusa
promoção legítima, ou alguém promove de novo sem saber que já promoveu.

Duas invariantes foram para o **banco**, além do Pydantic: modelo
`APPROVED`/`PROMOTED` sem evidência (`CHECK`) e duas versões `ACTIVE` do mesmo
asset (índice único parcial).

Trilha de correlação, comparações de shadow, janela de SLI e avaliações de
política ficam em memória **por escolha**, com o motivo declarado em
`EPHEMERAL_BY_DESIGN`.

### Disaster Recovery provado contra banco real

O ensaio real encontrou uma falha silenciosa: o runner de migrations é
idempotente, então tabelas destruídas com o livro-razão intacto **não são
recriadas** — o operador vê "aplicadas: 0" e conclui que está tudo certo.
Virou procedimento explícito em `disaster_recovery/postgres.py`.

### Rename

- Comando canônico `veltrix`; `pedrocore` continua como alias.
- Cabeçalhos `X-Veltrix-*`; `X-PedroCore-*` continua aceito.
- Variáveis `VELTRIX_*`; `PEDROCORE_*` continua aceito. As duas com valores
  diferentes **recusam** a configuração em vez de escolher em silêncio.
- Pacotes `veltrix-api` e `veltrix-web`; pasta de docs `Veltrix/`.

**Preservados de propósito:** identificadores de contrato (`pedrocore-*/v1`),
docstrings dos modelos de contrato (viram `description` no JSON Schema e entram
no fingerprint), tabelas `pedrocore_*`, `project_id="pedrocore"` e a chave de
armazenamento do navegador.

Verificação: 1789 testes com PostgreSQL real, 1750 em paridade com a CI, ruff
limpo, frontend 117 verde, grafo 175/1022/0, 6 fingerprints V1 intactos,
`npm audit` 0 vulnerabilidades.

## Platform Evolution — 12 evoluções de plataforma

Doze evoluções implementadas sobre o Veltrix existente, sem reconstruí-lo.
Detalhe por evolução em `Veltrix/16-plataforma/PLATFORM_EVOLUTION_FINAL_STATE.md`.

- **Consumer SDK** — cliente oficial tipado, neutro em relação ao projeto,
  com retry só onde repetir é seguro, idempotência derivada do conteúdo e
  erro sanitizado.
- **Policy Engine** — decisão transversal versionada e explicável. As três
  invariantes da arquitetura viraram regras executáveis com teste negativo.
- **Control Center** — agregação somente leitura (rota + `pedrocore
  control-center`). A UI React não foi alterada.
- **Evaluation Plane V2** — avaliação como evidência reproduzível.
  `DATASET_NOT_READY` continua válido; métrica sem dataset é descartada.
- **Model Registry + Promotion** — ciclo de vida explícito; promoção exige
  `evaluation_id` e rollback é sempre possível.
- **Shadow Mode** — observação paralela que não responde, não executa, não
  persiste e não duplica efeito.
- **Routing por qualidade/custo/latência** — eliminação antes de ordenação;
  pesos declarados por estratégia; seleção fora do ranking é recusada.
- **Prompt & Configuration Registry** — assets governados versionados, com
  hash conferido e segredo recusado na entrada.
- **Unified Audit / Correlation** — `correlation_id` transversal; a trilha
  guarda ponteiro, nunca conteúdo.
- **SLO / Health** — sem medição o indicador é `UNKNOWN`, nunca `HEALTHY`.
- **Compatibility Matrix** — resposta calculada, sem tabela por projeto.
- **Disaster Recovery** — restauração provada destruindo estado descartável
  antes de restaurar.

Verificação: 1744 testes com PostgreSQL real, 1722 em paridade com a CI, ruff
limpo, frontend 117 verde, grafo 173/1012/0, contratos V1 intactos e OpenAPI
aditivo (40 → 43 paths, 166 → 180 schemas, zero remoção).

## Risk Engine V2 — fechamento de produto

Console, CLI e porta HTTP sobre o motor já fechado em R0–R5. O motor não mudou.

- **Risk Console** — TUI em Textual (`pedrocore risk`), em PT-BR, consumindo o
  core no mesmo processo. Não decide risco: o gate vem da política.
- **CLI** — `analyze`, `inspect`, `contract`, `validate-contract`, `history`,
  `benchmark`. Código de saída próprio para `BLOCK`. Saída `--json` em UTF-8.
- **R4 HTTP** — `POST /api/risk/universal/analyze`, porta operacional do
  contrato universal de risco. Fecha a dívida do fechamento anterior.
- **PostgreSQL real** — os 22 casos antes `skip` executados contra banco
  descartável: migrations 0009 e 0010, insert/read, durabilidade,
  idempotência, conflito, isolamento de projeto, histórico e métrica de blast.
- **Arquitetura** — `risk_console` declarado no Runtime Plane.

Aditivo: OpenAPI ganha 1 rota e 2 schemas; nada removido, nenhum `required`
novo, nenhum tipo alterado. A UI React principal não foi alterada.

## [Não lançado] — AI Runtime & Learning Control Plane

Reorganização arquitetural em dez Eras. **Zero breaking change**: nenhuma rota,
schema ou contrato público existente foi removido ou alterado.

### Adicionado

- **Risk Engine V2 — R0 a R5** (`Veltrix/15-risk-engine/RISK_ENGINE_V2_BASELINE.md`).
  Persistência própria do domínio Risk (migrations `0009` e `0010`), Historical
  Risk consumindo esse store, métrica quantitativa de blast radius, contrato
  universal `pedrocore-risk-request/v1` e Scenario Simulation V2 com cenários
  relevantes ao payload. Os cinco problemas do baseline (P1–P5) fechados, cada
  um com teste e verificação por mutação.

- **`LICENSE` — Apache License 2.0** (SPDX `Apache-2.0`), com a metadata
  correspondente em `apps/api/pyproject.toml` (`License-Expression`) e
  `apps/web/package.json`.

- **Fronteiras de plano declaradas e verificadas** (`app/architecture/planes.py`).
  Runtime Plane, Learning Plane, Shared Kernel e Consumer Capabilities. Um
  módulo novo sem plano declarado quebra o build; a direção da dependência é
  testada.
- **Universal Contracts V1** (`app/modules/universal_contracts/`): Project
  Capability Manifest, Quality Evidence (QEC), Execution Outcome, Learning
  Source e o envelope de integração. Todos versionados e congelados por
  fingerprint de JSON Schema.
- **Fronteira de autoridade** (`universal_contracts/authority.py`). Um payload
  que tente emitir julgamento reservado ao servidor — `eligibility`,
  `authorized`, `training_candidate`, `quality_score`, `readiness`,
  `automatic_collection` — é recusado inteiro, em qualquer profundidade e
  qualquer grafia.
- **Project Capability Manifest** (`project_context/manifests.py`). O core
  passou a perguntar *o que o consumidor declara saber fazer* em vez de *quem
  ele é*.
- **Evidence Platform** (`app/modules/evidence_platform/`) com ingestão
  fail-closed, varredura de privacidade antes da persistência, fingerprint
  derivado pelo servidor, idempotência e deduplicação.
  Rotas aditivas: `POST/GET /api/evidence/{project_id}`.
- **Promoção governada de evidência** para o Learning Plane: nova origem
  `evidence_record`, com teto de propósito por tipo de evidência.
- **Resiliência de integração** (`app/modules/resilience/`): outbox local de
  referência com backoff exponencial e dead-letter, mais reconciliação.
  Rota aditiva: `POST /api/evidence/{project_id}/reconcile`.
- **Dataset Control Plane** (`app/modules/dataset_registry/`): registry,
  versionamento, linhagem completa e split determinístico por fingerprint. A
  materialização é travada por readiness real.
- **Evaluation & Training Foundation** (`app/modules/training_foundation/`):
  registry de avaliação, comparação com baseline, política de promoção e
  rollback, com abstração de backend de treino.
- **Migration `0006_evidence_records.sql`**, aditiva, com isolamento de projeto
  como chave primária e deduplicação garantida pelo banco.
- **Contract freeze** (`tests/test_contract_freeze.py`): alterar a forma de um
  contrato V1 quebra o build.
- **Outbox durável** (`resilience/durable_outbox.py`) em arquivo (escrita
  atômica) ou PostgreSQL, com migration `0007_outbox_entries.sql`. O outbox
  agora sobrevive ao restart do processo consumidor.
- **Persistência do Dataset Registry** (`dataset_registry/repository.py`) com
  migration `0008_dataset_registry.sql`. Definições, versões e linhagem
  sobrevivem ao restart.
- **Factories de persistência** (`resilience/factory.py`,
  `dataset_registry/factory.py`): a implementação durável passou a ser
  realmente construída em produção, pela mesma variável de ambiente do resto do
  sistema. Antes, `DurableOutboxStore` só era instanciado em teste.
- **Segurança contra corrupção** (`resilience/storage.py`): arquivo ilegível
  entra em estado degradado com cópia em quarentena, em vez de virar store
  vazio e ser sobrescrito na escrita seguinte.
- `tests/test_durability.py` (18 testes de restart real),
  `tests/test_durability_hardening.py` (21 de corrupção e wiring) e
  `tests/test_migrations_structure.py` (validação offline das migrations).
- `SECURITY.md`, `CONTRIBUTING.md` e workflow de CI.

### Alterado

- `orchestration/service.py` passou a importar a maquinaria do Learning Plane
  de forma **tardia**. O invariante "se o aprendizado falhar, o assistente
  continua respondendo" passou a valer também em tempo de importação.
- Quatro decisões por nome de projeto no core genérico foram substituídas por
  capability/trait declarativos (`orchestration`, `prompt_builder`,
  `artifact_reader`, `exploration/playwright_adapter`).
- Os padrões de detecção de segredo, credencial, PII e dado financeiro foram
  extraídos para o Shared Kernel e passaram a ser **fonte única** para a
  ingestão e para a promoção a candidato.
- `TrainingSourceType` ganhou o valor `evidence_record`. **Mudança aditiva** —
  nenhum valor removido, nenhuma outra chave alterada.
- `audit` e `observability` foram reclassificados do Shared Kernel para o
  Runtime Plane, porque dependem de `provider_binding`, `orchestration` e
  `evaluation`. A reclassificação foi forçada pelo próprio teste de fronteira.

### Corrigido

- **`finguard-local` nunca recebia a regra de segurança read-only.** A
  comparação `project_id == "finguard"` não alcançava `"finguard-local"`. O
  modelo por trait corrigiu o caso, junto de `structa` e `elyra`, que também
  são externos e read-only.
- Mensagens de bloqueio deixaram de nomear consumidores específicos: um aviso
  que nomeia um sistema revela a terceiros quais o Veltrix conhece.
- `postcss` atualizado de 8.5.15 para 8.5.26 (duas vulnerabilidades altas,
  transitivas via `vite`, apenas em tempo de build). Saída do build inalterada.
- **`pip install -e .` falhava** com "Multiple top-level packages discovered in
  a flat-layout: ['app', 'migrations']". Defeito pré-existente que o passo de
  instalação da CI teria encontrado na primeira execução. Corrigido com
  descoberta explícita de pacotes (`[tool.setuptools.packages.find]`); o wheel
  agora inclui `app` e exclui `migrations`, que são SQL aplicado por um runner
  e não um pacote Python.
- Duas contagens de arquivo publicadas em relatórios intermediários estavam
  erradas por contar uma pasta de documentação como uma linha; recontadas a
  partir do Git e corrigidas na documentação.

### Segurança

- `automatic_collection` permanece `Literal[False]`: um tipo que faz o
  validador recusar `True`, não uma flag desligada.
- `derived_content_only` é `Literal[True]` no contrato de fonte de
  aprendizado — conteúdo bruto não entra por esse caminho.
- Achados de privacidade reportam código, categoria e caminho — **nunca o
  valor detectado**.
- Mensagens de erro de contrato não ecoam o payload recusado.

### Não incluído (por decisão de escopo)

Nenhum treinamento, fine-tuning, LoRA ou SFT real; nenhum dataset canônico
materializado; nenhuma integração com Hugging Face ou GPU cloud; nenhum modelo
promovido a produção; nenhuma migração de FinGuard, Structa ou Elyra.

```text
CONTROL_PLANE_READY      governança completa e testada
DATASET_NOT_READY        correto — não há população real autorizada
```

### Verificação

```text
backend      1340 passed, 21 skipped, 0 failed
ruff         All checks passed!
frontend     tsc -b && vite build PASS
npm audit    0 vulnerabilities (produção)
docs graph   161 documentos, 858 links, zero violações
openapi      37 → 39 paths, 156 → 163 schemas, zero breaking change
```
