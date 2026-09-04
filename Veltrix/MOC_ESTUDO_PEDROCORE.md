# MOC Estudo — Study Pack atual do Veltrix

Atualizado em: 03/09/2026

Este é o **Study Pack atual do Veltrix**: o material para aprender (ou
reaprender, meses depois) o sistema que realmente existe hoje. O nome do
arquivo é histórico; o conteúdo não.

Voltar para a entrada do grafo: [[MOC_VELTRIX]].

---

## Sequência recomendada

Leia nesta ordem. Cada passo pressupõe o anterior.

| # | Documento | O que você sai sabendo |
|---|---|---|
| 1 | [[15-estudo-pedrocore/PEDROCORE_RESUMO_EXECUTIVO]] | o que o Veltrix é, os dois planos, estado atual, freeze |
| 2 | [[15-estudo-pedrocore/VELTRIX_LINHA_DO_TEMPO]] | como um chat virou um control plane; o rename; os três eixos de versão |
| 3 | [[15-estudo-pedrocore/PEDROCORE_MAPA_MENTAL]] | a forma do sistema em árvore |
| 4 | [[15-estudo-pedrocore/PEDROCORE_FLUXO_COMPLETO]] | os quatro fluxos, os seis estados de provider, a semântica do fallback |
| 5 | [[15-estudo-pedrocore/VELTRIX_RISK_ENGINE_ESTUDO]] | o maior subsistema: V1 → V2, P1–P5, Console, Project Registry |
| 6 | [[15-estudo-pedrocore/PEDROCORE_GLOSSARIO]] | vocabulário preciso |
| 7 | [[15-estudo-pedrocore/PEDROCORE_PERGUNTAS_E_RESPOSTAS]] | 34 perguntas com resposta direta |
| 8 | [[15-estudo-pedrocore/PEDROCORE_FLASHCARDS]] | revisão ativa; conceitos duráveis |

## Ferramentas de estudo

- [[15-estudo-pedrocore/PEDROCORE_ROTEIRO_NOTEBOOKLM]] — 19 fontes verificadas
  e prompts para NotebookLM.
- [[15-estudo-pedrocore/PEDROCORE_ROTEIRO_CLAUDE_OBSIDIAN]] — como fazer um
  agente ler este vault sem confundir história com presente.

## Auditorias históricas — preservadas, **não** são estado atual

- [[15-estudo-pedrocore/PEDROCORE_AUDITORIA_STUDY_MAP_01]] — **HISTÓRICO**:
  auditoria local de 09/07/2026 (HEAD `e0ff8e3`, `296 passed`). Evidência
  preservada sem alteração.
- [[15-estudo-pedrocore/PEDROCORE_VEREDITO_FINAL]] — **SUPERSEDED**: veredito de
  09/07/2026. Trata publicação e commit como futuros; ambos já aconteceram.

## Fontes canônicas por assunto

**Estado e fechamento**
- [[19-encerramento-final/VELTRIX_FINAL_FUNCTIONAL_GATE]] — fechamento canônico
- [[09_STATUS_ATUAL]] — estado corrente no topo, histórico abaixo
- [[17-veltrix/VELTRIX_FINAL_STATE]] — descrição arquitetural

**Arquitetura e plataforma**
- [[20-control-plane/PEDROCORE_CONTROL_PLANE_FINAL_STATE]] — Eras 1–10
- [[20-control-plane/PEDROCORE_UNIVERSAL_CONTRACTS_REFERENCE]] — os cinco contratos
- [[16-plataforma/PLATFORM_EVOLUTION_FINAL_STATE]] — as doze evoluções
- [[17-veltrix/MIGRACAO_PEDROCORE_VELTRIX]] — o rename e o que não mudou

**Risk Engine**
- [[15-risk-engine/RISK_ENGINE_V2_BASELINE]] · [[15-risk-engine/RISK_CONSOLE]] ·
  [[15-risk-engine/PROJECT_REGISTRY]]
- [[15-risk-engine/RISK_ENGINE_FOUNDATION]] ·
  [[15-risk-engine/PRE_EXECUTION_RISK_V1]] ·
  [[15-risk-engine/EXECUTION_CONTRACT_RISK_GATES]] ·
  [[15-risk-engine/POST_EXECUTION_QA]] ·
  [[15-risk-engine/HISTORICAL_RISK_INTELLIGENCE]]

**Learning e dataset**
- [[16-training-data/DATASET_FOUNDATION]] ·
  [[16-training-data/TRAINING_CANDIDATE_LIFECYCLE]] ·
  [[16-training-data/DATASET_READINESS_AUDIT]]
- [[14-intelligence-layer/OPERATIONAL_MEMORY]] ·
  [[14-intelligence-layer/RETRIEVAL_V1]] ·
  [[14-intelligence-layer/SAFE_REUSE_FOUNDATION]]
- [[14-intelligence-layer/INTELLIGENCE_LAYER_OVERVIEW]] ·
  [[14-intelligence-layer/REPORT_MEMORY]] ·
  [[14-intelligence-layer/EVAL_HARNESS]]

**Hubs**
- [[MOC_ARQUITETURA]] · [[MOC_SEGURANCA]] · [[MOC_TESTES]] ·
  [[MOC_QA_RELEASE_GATE]] · [[MOC_QA_SAFETY_HARDENING]] ·
  [[MOC_VERSOES_STATUS]] · [[MOC_FECHAMENTOS]]

**Fechamentos históricos citados no estudo**
- [[13-fechamento/FECHAMENTO_PEDROCORE_FINAL]] ·
  [[13-fechamento/FECHAMENTO_PEDROCORE_MODEL_FOUNDATION_01]] ·
  [[13-fechamento/FECHAMENTO_PEDROCORE_ECOSYSTEM_INTELLIGENCE_SUITE_01]] ·
  [[16-qa-safety-hardening/FECHAMENTO_PEDROCORE_QA_SAFETY_HARDENING_01]] ·
  [[19-encerramento-final/PEDROCORE_FECHAMENTO_DOCUMENTAL_FINAL_ERAS_1_A_3]]

---

## Limites que o estudo nunca deve ultrapassar

- O Veltrix é um control plane de IA, **não** um modelo treinado.
- Operational Learning existe e é determinístico; **não** altera pesos neurais.
- Não há fine-tuning, dataset canônico gerado, splits, PEFT/LoRA/SFT nem RAG
  vetorial.
- Report Memory **não** treina IA.
- O adapter `local_model` **não** é um Local Provider treinado, e não tem
  transport real.
- Provider real permanece bloqueado por padrão.
- O Risk Engine **não** executa nada.
- `CONTROL_PLANE_READY` **não** significa `DATASET_READY`.
- `pedrocore` minúsculo é identificador técnico preservado, **não** branding
  esquecido.
