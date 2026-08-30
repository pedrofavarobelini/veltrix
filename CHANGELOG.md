# Changelog

Mudanças relevantes do PedroCore IA.

O histórico detalhado por versão de produto (V1 a V5.1.9) está em
`PedroCore IA/08_CHANGELOG.md` e permanece a fonte para aquele período.
Este arquivo começa no programa **AI Runtime & Learning Control Plane**.

Formato: [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

---

## [Não lançado] — AI Runtime & Learning Control Plane

Reorganização arquitetural em dez Eras. **Zero breaking change**: nenhuma rota,
schema ou contrato público existente foi removido ou alterado.

### Adicionado

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
  que nomeia um sistema revela a terceiros quais o PedroCore conhece.
- `postcss` atualizado de 8.5.15 para 8.5.26 (duas vulnerabilidades altas,
  transitivas via `vite`, apenas em tempo de build). Saída do build inalterada.
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
backend      1273 passed, 21 skipped, 0 failed
ruff         All checks passed!
frontend     tsc -b && vite build PASS
npm audit    0 vulnerabilities (produção)
docs graph   161 documentos, 858 links, zero violações
openapi      37 → 39 paths, 156 → 163 schemas, zero breaking change
```
