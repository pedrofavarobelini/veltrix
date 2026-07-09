# MOC PedroCore IA

Entrada principal do grafo Obsidian do PedroCore IA.

## Mapas centrais

- [[00_MAPEAMENTO_GERAL_PEDROCORE]] - mapa completo atual do sistema.
- [[MOC_ARQUITETURA]] - camadas, endpoints e modulos.
- [[MOC_SEGURANCA]] - safe mode, policy, providers reais, reader e limites.
- [[MOC_QA_RELEASE_GATE]] - QA textual, release gate e evidencias.
- [[MOC_INTEGRACOES]] - FinGuard e contratos externos.
- [[MOC_TESTES]] - comandos, suite padrao e testes opt-in.
- [[MOC_VERSOES_STATUS]] - versoes, tags, status e changelog.

## Documentos oficiais atuais

- `README.md` (raiz do repositório)
- `VERSION.md` (raiz do repositório)
- [[09_STATUS_ATUAL]]
- [[08_CHANGELOG]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_FINAL]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01]]
- [[13-fechamento/FECHAMENTO_PEDROCORE_ECOSYSTEM_INTELLIGENCE_SUITE_01]]

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

## Contexto historico util

- [[13-fechamento/FECHAMENTO_PEDROCORE_REPLAN_01]]
- [[13-fechamento/PREPARACAO_TAG_V6_0_0]]
- [[03-versoes/ROADMAP]]
- [[07-decisoes/DECISOES_TECNICAS]]

## Navegacao rapida

- Para entender o sistema inteiro: [[00_MAPEAMENTO_GERAL_PEDROCORE]].
- Para testar sem risco: [[MOC_TESTES]].
- Para integracao FinGuard: [[MOC_INTEGRACOES]].
- Para checar status/tag: [[MOC_VERSOES_STATUS]].
