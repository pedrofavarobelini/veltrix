# MOC Estudo PedroCore

Mapa das notas de estudo e auditoria em `PedroCore IA/15-estudo-pedrocore/`.

## Entrada principal

- [[19-encerramento-final/PEDROCORE_FECHAMENTO_DOCUMENTAL_FINAL_ERAS_1_A_3]] -
  estado consolidado e didático das Eras 1–3.
- [[MOC_PEDROCORE_IA]] - mapa principal do PedroCore IA.
- [[00_MAPEAMENTO_GERAL_PEDROCORE]] - mapa tecnico completo e estado canonico.
- [[MOC_ARQUITETURA]] - arquitetura, endpoints e modulos.
- [[MOC_SEGURANCA]] - guardrails e limites.
- [[MOC_QA_RELEASE_GATE]] - QA textual e release gate.
- [[MOC_QA_SAFETY_HARDENING]] - safety hardening pos-auditoria.
- [[MOC_VERSOES_STATUS]] - status, roadmap, changelog e fechamentos.

## Notas de estudo

- [[15-estudo-pedrocore/PEDROCORE_RESUMO_EXECUTIVO]] - resumo para leitura rapida.
- [[15-estudo-pedrocore/PEDROCORE_MAPA_MENTAL]] - organizacao mental dos modulos e limites.
- [[15-estudo-pedrocore/PEDROCORE_FLUXO_COMPLETO]] - fluxo ponta a ponta do `/api/orchestrate`.
- [[15-estudo-pedrocore/PEDROCORE_GLOSSARIO]] - conceitos centrais e termos de seguranca.
- [[15-estudo-pedrocore/PEDROCORE_PERGUNTAS_E_RESPOSTAS]] - perguntas frequentes e respostas tecnicas.
- [[15-estudo-pedrocore/PEDROCORE_FLASHCARDS]] - revisao ativa de conceitos.
- [[15-estudo-pedrocore/PEDROCORE_ROTEIRO_NOTEBOOKLM]] - fontes e prompts para NotebookLM.
- [[15-estudo-pedrocore/PEDROCORE_ROTEIRO_CLAUDE_OBSIDIAN]] - roteiro de revisao e notas Obsidian.
- [[15-estudo-pedrocore/PEDROCORE_AUDITORIA_STUDY_MAP_01]] - auditoria local e evidencias de readiness.
- [[15-estudo-pedrocore/PEDROCORE_VEREDITO_FINAL]] - veredito final e proximos passos.

## Fontes tecnicas relacionadas

- [[14-intelligence-layer/OPERATIONAL_MEMORY]] - padrões, evidências, confidence e lifecycle.
- [[14-intelligence-layer/RETRIEVAL_V1]] - retrieval bounded e FTS sem embeddings.
- [[14-intelligence-layer/SAFE_REUSE_FOUNDATION]] - modos de reuse sem provider bypass.
- [[15-risk-engine/RISK_ENGINE_FOUNDATION]] - fundação do Motor de Risco.
- [[15-risk-engine/HISTORICAL_RISK_INTELLIGENCE]] - métricas e comparação de estratégias.
- [[16-training-data/DATASET_FOUNDATION]] - dado operacional, candidato e exemplo canônico.
- [[16-training-data/TRAINING_CANDIDATE_LIFECYCLE]] - aquisição, autorização, privacy e lifecycle.
- [[16-training-data/DATASET_READINESS_AUDIT]] - `DATASET_NOT_READY` e zero candidatos reais autorizados.
- [[14-intelligence-layer/INTELLIGENCE_LAYER_OVERVIEW]] - Intelligence Layer, `local_model`, Report Memory e limites.
- [[14-intelligence-layer/EVAL_HARNESS]] - harness deterministico.
- [[14-intelligence-layer/REPORT_MEMORY]] - memoria tecnica controlada; nao e treinamento.
- [[13-fechamento/FECHAMENTO_PEDROCORE_FINAL]] - fechamento local `v7.0.0`.
- [[13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01]] - fundacao de inteligencia propria.
- [[13-fechamento/FECHAMENTO_PEDROCORE_ECOSYSTEM_INTELLIGENCE_SUITE_01]] - inteligencia de ecossistema.
- [[16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01]] - safety hardening posterior ao estudo.

## Limites de leitura

- PedroCore IA e orquestrador central, nao modelo treinado.
- Operational Learning está implementado; não altera pesos neurais.
- Nao ha fine-tuning, dataset canônico, splits ou RAG vetorial real.
- Report Memory nao treina IA.
- O adapter/contrato `local_model` não é Local Provider treinado.
- Provider real permanece bloqueado por padrao.
