# PedroCore IA — Versionamento

Atualizado em: 20/08/2026

## Checkpoint documental atual

O fechamento das Eras 1–3 não altera versão de produto, pacote ou tag:

```text
Era 1  PASS
Era 2  PASS
Era 3  FOUNDATION PASS / TRAINING DEFERRED
```

Candidate Acquisition Foundation está implementada; candidatos reais
autorizados permanecem em zero e o resultado é `DATASET_NOT_READY`. Canonical
Dataset, splits, Hugging Face, fine-tuning, modelo próprio e Local Provider
treinado não foram entregues. Ver
`PedroCore IA/19-encerramento-final/PEDROCORE_FECHAMENTO_DOCUMENTAL_FINAL_ERAS_1_A_3.md`.

## As três numerações — leia isto antes de comparar números

O projeto tem **três** eixos de versão independentes. Confundi-los é a fonte
mais comum de leitura errada da documentação.

| Eixo | Valor atual | O que marca |
| --- | --- | --- |
| **Produto (UI)** | `V5.2.0` | Entregas visuais/funcionais do frontend. É o rótulo exibido na interface. |
| **Técnica (API)** | `0.2.0` | Versão do pacote Python em `apps/api/pyproject.toml` e em `FastAPI(version=…)`. |
| **Marco Git (tag)** | `v7.0.0` | Marcos técnicos do repositório. **Não** acompanha o produto. |

Consequência a ter em mente: a tag `v6.0.0` marca o **MVP backend**, e não a
versão 6 do produto. Produto e tag nunca foram sincronizados e não devem ser.

## Versão atual de produto

**V5.2.0** — elevada de `V5.1.9` por `PEDROCORE-V1-FINAL-CLOSURE`.

É um **minor** da linha 5.x porque a frente acrescentou recursos de interface —
composer único, drawer de Configurações, ditado por voz e anexos textuais — sem
quebrar nenhum contrato de API. Nenhuma numeração histórica foi renumerada.

Não foi escolhido `V6.0.0` deliberadamente: colidiria com a leitura da tag
`v6.0.0`, que significa outra coisa.

## Versão técnica do backend

`0.2.0` (`apps/api/pyproject.toml`) — **sem alteração**. Nenhum arquivo de
`apps/api/` foi modificado por esta frente.

## Frente atual — PEDROCORE-V1-FINAL-CLOSURE

Fechamento da interface pública da V1. Mapa: `PedroCore IA/MOC_UX_V1.md`.
Relatório: `PedroCore IA/20-ux-v1/PEDROCORE_V1_FINAL_CLOSURE_01.md`.

- Composer único com seletor de IA, anexos e microfone; Configurações em drawer
  acessível; sem cards de provider no topo.
- Modo DEV coerente: `mock` é destino de conversa com selo `DEV`; `auto`,
  `local_qa` e `local_model` não são destinos e passaram a ser exibidos como
  referência não selecionável.
- Voz sem gravar, guardar ou transmitir áudio.
- Anexos textuais pelo contrato `artifacts` já existente — nenhum endpoint novo.
- Primeira suíte de testes do frontend: `86 passed`, com versões **exatas**.
- Multimodal adiado formalmente para a V2.
- Validação: backend `751 passed, 7 skipped, 2 warnings`; frontend `86 passed`;
  typecheck e build PASS; grafo documental íntegro.
- Nenhuma tag criada nesta frente.

## Frente anterior — onboarding seguro do Structa

`PEDROCORE-STRUCTA-CONSUMER-01`.

- Project Context `structa`, somente `qa_report_analysis`.
- Caller Identity pelo `PEDROCORE_CALLER_REGISTRY`, com identidade
  `registered` e papel `technical_tool`.
- Gemini autorizado somente em ambiente não produtivo e somente após opt-in
  explícito; demais providers negados.
- `allow_real_provider=false` e fallback real false permanecem defaults.
- Validação offline: `751 passed, 7 skipped, 2 warnings`; zero inferências.
- Gate: [[PedroCore IA/17-multi-provider-safe-evolution/GATE_PEDROCORE_STRUCTA_CONSUMER_01]].

## Frente anterior — ENCERRAMENTO FINAL

`FINGUARD-PEDROCORE-CANONICAL-REPLAY-DOCS-GRAPH-FINALIZE-01`.

```text
PEDROCORE ENCERRADO — CORE OPERACIONAL CONCLUÍDO
```

- Assistente IA do FinGuard **homologado 4/4**: o cenário `Organizar` foi aprovado com Gemini real nesta frente (um único dispatch, `fallback=false`, `retry=0`). Os outros três cenários reaproveitam evidência real anterior já aprovada.
- Validação integral **medida após todas as alterações**: `736 passed, 7 skipped, 2 warnings`; eval `14/14`, `risk_level="none"`, sem chamadas externas reais na suíte.
- Grafo documental Obsidian íntegro: 128 documentos, 697 links resolvidos, zero órfãos, zero links quebrados, validado por `app.modules.docs_graph`.
- Nova capacidade de QA documental: `apps/api/app/modules/docs_graph/` + `tests/test_docs_graph.py`.
- Nenhuma implementação obrigatória restante.

Documento canônico: `PedroCore IA/19-encerramento-final/PEDROCORE_ENCERRAMENTO_FINAL_01.md`.

Vault canônico desde 2026-08-02: `PedroCore IA/`. A reorganização preservou
127/127 documentos anteriores; ver
`PedroCore IA/MANIFESTO_REORGANIZACAO_20260802.md`.

## Frente anterior (HISTÓRICO)

`PEDROCORE-MULTI-PROVIDER-DOCS-CONSOLIDATION-01`: fechamento documental das Etapas 1–7 da evolução multi-provider segura, tomando `e389b2c` como último commit de implementação. Catálogo, identidade/autorização, binding, shadow, enforced, health/circuit breaker e fallback pre-dispatch concluídos. Naquele momento a validação integral era `570 passed, 7 skipped, 2 warnings`. A arquitetura multi-provider está concluída; multi-provider automático operacional ainda não, pois somente `gemini + gemini-3.5-flash` está homologado e elegível.

Projeto **finalizado localmente**: `PEDROCORE-IMPLEMENT-05` (05A–05F, integrações reais controladas) e `PEDROCORE-FINALIZE-06` (06A enforcement final + 06B fechamento) concluídas. Tag final local: `v7.0.0`. Ver `PedroCore IA/13-fechamento/FECHAMENTO_PEDROCORE_FINAL.md`.

DOCFIX anterior: saneamento documental/Obsidian, sem alteração de código de produção, testes, tags, merge ou push. Mapeamento central: `PedroCore IA/00_MAPEAMENTO_GERAL_PEDROCORE.md`.

Frente anterior: `PEDROCORE-MODEL-FOUNDATION-01` — fundação de inteligência própria, commitada em `689e50a`. Testes na época: `257 passed, 6 skipped, 2 warnings`. Ver `PedroCore IA/13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01.md`.

Checkpoint histórico: `PEDROCORE-QA-SAFETY-HARDENING-01` — endurecimento QA/safety commitado em `d6106b7`. Naquele checkpoint: Pytest `341 passed, 6 skipped, 2 warnings`; eval harness `14/14 passed`, `risk_level="none"`. Ver `PedroCore IA/16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01.md`.

Frente documental anterior: `PEDROCORE-DOCS-GRAPH-LINKING-01` — linkagem Markdown/Obsidian em documentação, sem alteração de código.

O histórico de `FINGUARD-PEDROCORE-ASSISTANT-REAL-PROVIDER-QA-01` permanece registrado no changelog; o contrato comum atual do consumidor é `provider=auto` sem modelo, com decisão final no PedroCore.

## Status atual

`PEDROCORE-REPLAN-01` (01A a 01E) concluída no escopo documental. `PEDROCORE-IMPLEMENT-01A/01B` commitada em `577bc88`; `01C–01H` commitada em `95cbfab`; `PEDROCORE-IMPLEMENT-02` commitada em `e115672`. `PEDROCORE-IMPLEMENT-03` (MVP backend Blocos 1–7) commitada em `6ed4c41`: QA textual real por heurística local determinística, release gate conservador com `blocked_reason`, endpoint `POST /api/orchestrate` (pipeline centralizado, também usado por `/api/chat`), safe mode com `allow_real_provider=false` por padrão, autenticação interna opcional para `/api/orchestrate`, contrato padronizado de warnings/errors e audit não persistente completo. `PEDROCORE-FINALIZE-04` foi consolidada em `ee2ac68`, commit para o qual aponta a tag anotada `v6.0.0` com a mensagem `v6.0.0 - MVP backend PedroCore IA`. Testes backend passando (`125 passed, 2 warnings`). Sem alterações de frontend, design, providers reais ou `.env`.

## Tags atuais

`v7.0.0` é a tag final local do core operacional seguro e aponta para `33b2c0489c19776ef460fc85dea3c24298b46a3c`.

`v6.0.0` existe e aponta para `ee2ac68679feea6ac108abba8726d11da101576c` (`ee2ac68`). A tag representa o fechamento do MVP backend; ela não é a tag final local atual.

Resumo:

- `v6.0.0` = MVP backend.
- `v7.0.0` = fechamento técnico local do core operacional seguro.
- `d6106b7` = `PEDROCORE-QA-SAFETY-HARDENING-01`, hardening QA/safety posterior ao fechamento local.
- `62beff1` a `e389b2c` = Etapas 1–7 e correções da evolução multi-provider segura.
- Pendência obrigatória de código/teste/Git = zero no estado final registrado.
- Pendência operacional multi-provider = homologar um segundo provider/modelo real em frente separada.

## Observação sobre versionamento

A taxonomia completa está no topo deste documento. Registro histórico: nenhuma
das numerações foi alterada por `PEDROCORE-REPLAN-01` (01A a 01E); a versão de
produto passou de `V5.1.9` para `V5.2.0` apenas em `PEDROCORE-V1-FINAL-CLOSURE`.

## Próximos passos

### Decisão humana pendente

- **`LICENSE`** — não foi criada por decisão deliberada: escolher licença é
  decisão jurídica do proprietário, não do executor técnico. É o único item que
  impede a publicação no GitHub.

### Antes de expor a API na internet

- Autenticação obrigatória no `/api/chat`, rate limiting, teto de payload e TLS.
  Ver `PedroCore IA/20-ux-v1/MODELO_DE_AMEACA.md`.

### Opcionais, pós-fechamento

- V2 — Multimodal (imagem/PDF/DOCX): `PedroCore IA/20-ux-v1/V2_MULTIMODAL.md`.
- Homologar um segundo provider/modelo real em frente separada, escolhendo Claude ou OpenAI mediante decisão explícita.
- Execução real de OCR/Playwright somente com flags, dependências instaladas manualmente e revisão humana.
- Transport real do `local_model`; persistência da observabilidade.
- Saneamento adicional de documentos históricos duplicados dentro de `PedroCore IA/`, se o usuário quiser reduzir ruído do vault.
- Bloco 12 (dashboard/logs/admin): cancelado por decisão de produto — não é pendência.
