# MOC QA Release Gate

Mapa de QA textual, release gate e evidencias.

## Referencias atuais

- [[00_MAPEAMENTO_GERAL_PEDROCORE]] - secoes 9 e 10.
- [[13-fechamento/FECHAMENTO_PEDROCORE_FINAL]] - regras finais do release gate.
- [[10-api/EXEMPLOS_API_MVP]] - payloads seguros.
- [[08_CHANGELOG]] - historico de implementacao.

## Documentos de QA Intelligence

Estes documentos nasceram como planejamento e agora devem ser lidos com a nota de status atual:

- [[12-qa-intelligence/QA_INTELLIGENCE_OVERVIEW]]
- [[12-qa-intelligence/QA_REPORT_ANALYSIS]]
- [[12-qa-intelligence/QA_FAILURE_DIAGNOSIS]]
- [[12-qa-intelligence/QA_RELEASE_GATE]]
- [[10-contratos/CONTRATO_QA_INTELLIGENCE]]

## Codigo relacionado

- `apps/api/app/modules/qa_analysis/`
- `apps/api/app/modules/qa_response/`
- `apps/api/app/modules/artifacts/`
- `apps/api/app/modules/visual_qa/`
- `apps/api/app/modules/orchestration/`

## Testes relacionados

- `apps/api/tests/test_qa_analysis.py`
- `apps/api/tests/test_qa_response.py`
- `apps/api/tests/test_qa_flow.py`
- `apps/api/tests/test_release_gate.py`
- `apps/api/tests/test_release_hardening.py`
- `apps/api/tests/test_visual_qa.py`
- `apps/api/tests/test_multimodal_guard.py`
