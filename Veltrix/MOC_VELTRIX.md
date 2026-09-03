# MOC Veltrix

## Estado público atual

- [[17-veltrix/VELTRIX_FINAL_STATE]] — estado técnico consolidado.
- [[09_STATUS_ATUAL]] — status canônico corrente.
- Repositório público: `github.com/pedrofavarobelini/veltrix`, branch padrão
  `main`, sob Apache-2.0.
- **`HUMAN_VISUAL_ACCEPTANCE = PASS`**.
- Project Registry concluído; migrations atuais **`0001`–`0012`**.
- A CI do HEAD e `app.modules.docs_graph` são as fontes correntes para testes e
  integridade documental; contagens abaixo pertencem aos checkpoints nomeados.

## Consumer Elyra textual V1 — contrato vigente; gate histórico

- [[17-multi-provider-safe-evolution/PEDROCORE_ELYRA_ONBOARDING_V1_TEXTUAL]] —
  identidade própria, capability mínima, schemas strict, provider policy,
  correlation e idempotência.
- [[17-multi-provider-safe-evolution/GATE_PEDROCORE_ELYRA_ONBOARDING_V1_TEXTUAL]] —
  Gate PASS, `959 passed`, zero chamadas externas.
- [[10-contratos/CONTRATO_ELYRA_TEXTUAL_V1]] — contrato executável para a Stage
  09 consumir em execução separada.
## Eras 1–3 — escopo canônico; checkpoint histórico

- [[19-encerramento-final/PEDROCORE_FECHAMENTO_DOCUMENTAL_FINAL_ERAS_1_A_3]] —
  fechamento consolidado de Operational Intelligence, Risk Engine e Training
  Foundation.
- **Era 1:** PASS — Operational Intelligence Foundation.
- **Era 2:** PASS — Motor de Risco de Execução por IA.
- **Era 3:** FOUNDATION PASS / TRAINING DEFERRED.
- Training Candidates reais autorizados: **0**; readiness:
  **`DATASET_NOT_READY`**.
- Evidência backend daquele fechamento: `924 passed, 7 skipped, 2 warnings`;
  Ruff global PASS; Pyright Era 3 sem erros.

## UX V1 — ESTADO DE PRODUTO PRESERVADO

- [[MOC_UX_V1]] — mapa das frentes `PEDROCORE-V1-FINAL-CLOSURE` e
  `PEDROCORE-V1-FINAL-UI-FIX`: composer único, Configurações em drawer, catálogo
  correto das IAs públicas, modo DEV coerente, ditado por voz, anexos textuais
  reais e a primeira suíte de testes do frontend.
- [[20-ux-v1/PEDROCORE_V1_FINAL_CLOSURE_01]] — relatório final e gates.
- Versão de produto: **V5.2.0**. Backend: `0.2.0`, **inalterado** nas duas frentes.
- Snapshot daquela frente: backend `751 passed, 7 skipped`; frontend `117
  passed`; typecheck e build PASS.
- Grafo documental naquele checkpoint: 138 documentos, 800 links, zero órfãos
  e zero links quebrados.
- Multimodal (imagem/PDF/DOCX) **adiado formalmente**: [[20-ux-v1/V2_MULTIMODAL]].

## Consumer Structa — contrato vigente; gate histórico

- [[17-multi-provider-safe-evolution/PEDROCORE_STRUCTA_CONSUMER_01]] —
  onboarding least-privilege, registry oficial, Report Intelligence e zero
  inferências.
- [[17-multi-provider-safe-evolution/GATE_PEDROCORE_STRUCTA_CONSUMER_01]] —
  Gate próprio PASS; não é a Etapa 13 do Structa.

## Encerramento do core — HISTÓRICO PRESERVADO

- [[19-encerramento-final/PEDROCORE_ENCERRAMENTO_FINAL_01]] - **PEDROCORE ENCERRADO — CORE OPERACIONAL CONCLUÍDO**. Assistente IA homologado **4/4**; nenhuma implementação obrigatória restante.
- Suíte integral daquele checkpoint: `959 passed, 21 skipped`; eval `14/14`,
  `risk_level="none"`.
- Grafo documental daquele checkpoint: 155 documentos, 822 links resolvidos,
  zero órfãos e
  zero links quebrados, validado por `app.modules.docs_graph`.

## Fechamento anterior — 2026-07-27 (HISTÓRICO)

> Superado pelo encerramento final acima. A homologação 3/4 registrada nesta
> seção descrevia o estado antes da execução real do cenário Organizar.

- [[18-provider-output-budget-cancellation/PEDROCORE_ASSISTANT_FINAL_CLOSURE_01]] - **Assistente IA encerrado**, homologação real 3/4, Organizar como limitação externa aceita.
- [[18-provider-output-budget-cancellation/FECHAMENTO_PEDROCORE_PROVIDER_OUTPUT_BUDGET_CANCELLATION_01]] - orçamento de saída, timeout de transporte, cliente Gemini assíncrono e certeza de término.
- [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]] - mapa central das Etapas 1–7, correções e evolução posterior.
- [[17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7]] - fechamento técnico e documental consolidado.
- Suite integral mais recente: `703 passed, 7 skipped, 2 warnings`; eval `14/14`, `risk_level="none"`; zero chamadas externas reais.
- Arquitetura multi-provider concluída; automação multi-provider real ainda indisponível porque há somente um provider/modelo homologado e elegível.
- Cancelamento remoto continua não comprovável; `completion_ambiguous` preservado.

Entrada principal do grafo Obsidian do Veltrix.

## Mapas centrais

- [[00_MAPEAMENTO_GERAL_PEDROCORE]] - mapa completo atual do sistema.
- [[MOC_ARQUITETURA]] - camadas, endpoints e modulos.
- [[MOC_SEGURANCA]] - safe mode, policy, providers reais, reader e limites.
- [[MOC_QA_RELEASE_GATE]] - QA textual, release gate e evidencias.
- [[MOC_QA_SAFETY_HARDENING]] - frente `d6106b7` de endurecimento QA/safety.
- [[MOC_INTEGRACOES]] - FinGuard e contratos externos.
- [[MOC_TESTES]] - comandos, suite padrao e testes opt-in.
- [[MOC_VERSOES_STATUS]] - versoes, tags, status e changelog.
- [[MOC_UX_V1]] - interface pública: composer, drawer, voz, anexos e testes frontend.
- [[MOC_ESTUDO_PEDROCORE]] - notas de estudo e auditoria.
- [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]] - catálogo, identidade, binding, roteamento, health e fallback.
- [[MOC_FECHAMENTOS]] - todos os fechamentos de frente, do MVP ao encerramento final.
- [[MOC_HISTORICO_PEDROCORE]] - documentos históricos `V1`-`V5.1.9` e primeira organização da documentação.

## Documentos oficiais atuais

- `README.md` (raiz do repositório)
- `VERSION.md` (raiz do repositório)
- [[MANIFESTO_REORGANIZACAO_20260802]] - prova de preservação e nova raiz canônica do vault.
- [[09_STATUS_ATUAL]]
- [[08_CHANGELOG]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_FINAL]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_ECOSYSTEM_INTELLIGENCE_SUITE_01]]
- [[16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01]]
- [[17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7]]
- [[19-encerramento-final/PEDROCORE_FECHAMENTO_DOCUMENTAL_FINAL_ERAS_1_A_3]]

## Operational Intelligence, Risk Engine e Training Foundation

- [[14-intelligence-layer/REPORT_INTELLIGENCE_FOUNDATION]]
- [[14-intelligence-layer/REPORT_MEMORY]]
- [[14-intelligence-layer/INTERACTION_OUTCOMES]]
- [[14-intelligence-layer/OPERATIONAL_MEMORY]]
- [[14-intelligence-layer/RETRIEVAL_V1]]
- [[14-intelligence-layer/SAFE_REUSE_FOUNDATION]]
- [[15-risk-engine/RISK_ENGINE_FOUNDATION]]
- [[15-risk-engine/PRE_EXECUTION_RISK_V1]]
- [[15-risk-engine/EXECUTION_CONTRACT_RISK_GATES]]
- [[15-risk-engine/POST_EXECUTION_QA]]
- [[15-risk-engine/HISTORICAL_RISK_INTELLIGENCE]]
- [[16-training-data/DATASET_FOUNDATION]]
- [[16-training-data/TRAINING_CANDIDATE_LIFECYCLE]]
- [[16-training-data/DATASET_READINESS_AUDIT]]

## Fundação de inteligência própria (MODEL-FOUNDATION-01)

- [[14-intelligence-layer/INTELLIGENCE_LAYER_OVERVIEW]] - visao geral e glossario (provider externo/real/mock/local_qa/local_model, memoria, RAG, fine-tuning).
- [[14-intelligence-layer/REPORT_INTELLIGENCE_FOUNDATION]] - sinais de relatorios tecnicos; relatorios nao treinam IA.
- [[14-intelligence-layer/LOCAL_MODEL_PROVIDER_CONTRACT]] - contrato futuro do provider generativo local.
- [[14-intelligence-layer/EVALUATION_FOUNDATION]] - avaliacao deterministica de seguranca/coerencia.

## Inteligência de ecossistema (ECOSYSTEM-INTELLIGENCE-SUITE-01)

- [[10-contratos/CONTRATO_ECOSYSTEM_ASSISTANT]] - como sistemas consumidores usam o Veltrix.
- [[10-contratos/CONTRATO_REPORT_MEMORY]] - rotas e regras da memoria tecnica (default off).
- [[14-intelligence-layer/REPORT_MEMORY]] - memoria tecnica controlada; relatorios nao treinam IA.
- [[14-intelligence-layer/LOCAL_MODEL_PROVIDER]] - provider generativo local opt-in, sem rede nesta frente.
- [[14-intelligence-layer/EVAL_HARNESS]] - avaliacao deterministica; nao e benchmark de LLM.

## QA Safety Hardening (PEDROCORE-QA-SAFETY-HARDENING-01)

- [[MOC_QA_SAFETY_HARDENING]] - mapa da frente `d6106b7`.
- [[16-qa-safety-hardening/QA_SAFETY_HARDENING_PLAN]] - plano e escopo.
- [[16-qa-safety-hardening/MATRIZ_TASK_PROVIDER_POLICY]] - matriz task/provider/policy.
- [[16-qa-safety-hardening/RELEASE_GATE_CHECKLIST]] - checklist do release gate.
- [[16-qa-safety-hardening/REPORT_MEMORY_SAFETY]] - Report Memory default-off e nao treinamento.
- [[16-qa-safety-hardening/PROVIDER_REAL_SAFETY]] - provider real bloqueado por padrao.
- [[16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01]] - fechamento, pytest `341 passed` e eval harness `14/14`.

## Estudo e auditoria (PEDROCORE-AUDIT-STUDY-MAP-01)

- [[MOC_ESTUDO_PEDROCORE]] - mapa das notas de estudo.
- [[15-estudo-pedrocore/PEDROCORE_AUDITORIA_STUDY_MAP_01]] - relatorio documental da auditoria local.
- [[15-estudo-pedrocore/PEDROCORE_RESUMO_EXECUTIVO]] - resumo de estudo.
- [[15-estudo-pedrocore/PEDROCORE_MAPA_MENTAL]] - mapa mental em topicos.
- [[15-estudo-pedrocore/PEDROCORE_FLUXO_COMPLETO]] - fluxo completo do ecossistema.
- [[15-estudo-pedrocore/PEDROCORE_GLOSSARIO]] - glossario simples.
- [[15-estudo-pedrocore/PEDROCORE_PERGUNTAS_E_RESPOSTAS]] - perguntas e respostas.
- [[15-estudo-pedrocore/PEDROCORE_FLASHCARDS]] - flashcards.
- [[15-estudo-pedrocore/PEDROCORE_ROTEIRO_NOTEBOOKLM]] - roteiro NotebookLM.
- [[15-estudo-pedrocore/PEDROCORE_ROTEIRO_CLAUDE_OBSIDIAN]] - roteiro Claude + Obsidian.
- [[15-estudo-pedrocore/PEDROCORE_VEREDITO_FINAL]] - vereditos e proximos passos.

## Contexto historico util

- [[13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01]]
- [[13-fechamento/PREPARACAO_TAG_V6_0_0]]
- [[03-versoes/ROADMAP]]
- [[07-decisoes/DECISOES_TECNICAS]]

## Navegacao rapida

- Para entender o sistema inteiro: [[00_MAPEAMENTO_GERAL_PEDROCORE]].
- Para entender a interface atual: [[MOC_UX_V1]].
- Para avaliar risco de publicação/deploy: [[20-ux-v1/MODELO_DE_AMEACA]].
- Para testar sem risco: [[MOC_TESTES]].
- Para revisar QA/safety atual: [[MOC_QA_SAFETY_HARDENING]].
- Para integracao FinGuard: [[MOC_INTEGRACOES]].
- Para checar status/tag: [[MOC_VERSOES_STATUS]].
- Para estudar ou importar em LLM/notebook: [[MOC_ESTUDO_PEDROCORE]].
- Para entender a evolução multi-provider atual: [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]].
