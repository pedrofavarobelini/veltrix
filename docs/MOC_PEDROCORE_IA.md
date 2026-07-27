# MOC PedroCore IA

## Encerramento final — CANÔNICO ATUAL

- [[19-encerramento-final/PEDROCORE_ENCERRAMENTO_FINAL_01]] - **PEDROCORE ENCERRADO — CORE OPERACIONAL CONCLUÍDO**. Assistente IA homologado **4/4**; nenhuma implementação obrigatória restante.
- Suíte integral: `736 passed, 7 skipped`; eval `14/14`, `risk_level="none"`.
- Grafo documental íntegro: zero órfãos, zero links quebrados, validado por `app.modules.docs_graph`.

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

Entrada principal do grafo Obsidian do PedroCore IA.

## Mapas centrais

- [[00_MAPEAMENTO_GERAL_PEDROCORE]] - mapa completo atual do sistema.
- [[MOC_ARQUITETURA]] - camadas, endpoints e modulos.
- [[MOC_SEGURANCA]] - safe mode, policy, providers reais, reader e limites.
- [[MOC_QA_RELEASE_GATE]] - QA textual, release gate e evidencias.
- [[MOC_QA_SAFETY_HARDENING]] - frente `d6106b7` de endurecimento QA/safety.
- [[MOC_INTEGRACOES]] - FinGuard e contratos externos.
- [[MOC_TESTES]] - comandos, suite padrao e testes opt-in.
- [[MOC_VERSOES_STATUS]] - versoes, tags, status e changelog.
- [[MOC_ESTUDO_PEDROCORE]] - notas de estudo e auditoria.
- [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]] - catálogo, identidade, binding, roteamento, health e fallback.
- [[MOC_FECHAMENTOS]] - todos os fechamentos de frente, do MVP ao encerramento final.
- [[MOC_HISTORICO_PEDROCORE]] - documentos históricos `V1`-`V5.1.9` e primeira organização da documentação.

## Documentos oficiais atuais

- `README.md` (raiz do repositório)
- `VERSION.md` (raiz do repositório)
- [[09_STATUS_ATUAL]]
- [[08_CHANGELOG]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_FINAL]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_ECOSYSTEM_INTELLIGENCE_SUITE_01]]
- [[16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01]]
- [[17-multi-provider-safe-evolution/FECHAMENTO_ETAPAS_1_A_7]]

## Fundação de inteligência própria (MODEL-FOUNDATION-01)

- [[14-intelligence-layer/INTELLIGENCE_LAYER_OVERVIEW]] - visao geral e glossario (provider externo/real/mock/local_qa/local_model, memoria, RAG, fine-tuning).
- [[14-intelligence-layer/REPORT_INTELLIGENCE_FOUNDATION]] - sinais de relatorios tecnicos; relatorios nao treinam IA.
- [[14-intelligence-layer/LOCAL_MODEL_PROVIDER_CONTRACT]] - contrato futuro do provider generativo local.
- [[14-intelligence-layer/EVALUATION_FOUNDATION]] - avaliacao deterministica de seguranca/coerencia.

## Inteligência de ecossistema (ECOSYSTEM-INTELLIGENCE-SUITE-01)

- [[10-contratos/CONTRATO_ECOSYSTEM_ASSISTANT]] - como sistemas consumidores usam o PedroCore.
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
- Para testar sem risco: [[MOC_TESTES]].
- Para revisar QA/safety atual: [[MOC_QA_SAFETY_HARDENING]].
- Para integracao FinGuard: [[MOC_INTEGRACOES]].
- Para checar status/tag: [[MOC_VERSOES_STATUS]].
- Para estudar ou importar em LLM/notebook: [[MOC_ESTUDO_PEDROCORE]].
- Para entender a evolução multi-provider atual: [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]].
