# Task Router

> Nota DOCFIX: este documento nasceu como planejamento. Em `v7.0.0`, o módulo existe em `apps/api/app/modules/task_router/`. Use [[../00_MAPEAMENTO_GERAL_PEDROCORE]] para o estado atual completo.

## Responsabilidade atual

O Task Router é o primeiro módulo lógico a processar uma requisição de orquestração, responsável por:

- Receber o `task_type` da requisição.
- Interpretar o `origin_system` (e o `source`, se presente) para aplicar regras específicas por sistema chamador.
- Identificar a natureza da tarefa: chat comum, explicação técnica, análise de QA, análise de log, revisão de roadmap, etc.
- Decidir a **estratégia de resposta**: se a resposta pode ser texto livre ou precisa ser estruturada (ver `docs/10-contratos/CONTRATO_ORQUESTRACAO.md`, seção 3, e `CONTRATO_QA_INTELLIGENCE.md`).
- Indicar se o `MockProvider` pode ser usado para aquela tarefa, se `local_qa` é o caminho seguro ou se provider real exigiria autorização/revisão humana.
- Acionar o Prompt Builder já com a estratégia definida (tipo de tarefa, formato de resposta esperado, nível de criticidade).

## Regra de responsabilidade

**Task Router decide. Prompt Builder monta. Provider executa.** O Task Router nunca monta prompt final nem chama provider diretamente — ele apenas decide a estratégia e repassa para o Prompt Builder.

## Exemplos de roteamento

| `task_type` | Formato de resposta | Uso de Mock | Provider real |
|---|---|---|---|
| `general_chat` | Livre | Permitido, sem restrição | Não exigido |
| `technical_explanation` | Livre ou semi-estruturada | Permitido em desenvolvimento | Recomendado em uso real, não obrigatório |
| `qa_report_analysis` | Estruturada (obrigatória) | Não confiável para validação crítica — apenas para teste de integração | Obrigatório para análise real (Decisão Técnica 020) |
| `release_gate_review` | Estruturada (obrigatória) | Fallback para Mock deve **bloquear a conclusão** da tarefa, não gerar uma resposta como se fosse válida | Obrigatório, dado o caráter crítico |
| `visual_qa_analysis` | Estruturada (obrigatória) | Apenas para teste de integração | QA visual real exigiria suporte multimodal e aprovação; hoje há stub conservador |

O conjunto implementado atual inclui `general_chat`, `technical_explanation`, `code_help`, `qa_report_analysis`, `qa_failure_diagnosis`, `release_gate_review`, `artifact_summary`, `exploratory_test_plan`, `manual_exploration_report`, `assisted_exploration_review` e `unknown`.

## Estado de implementação

Implementado em `apps/api/app/modules/task_router/`. Ele normaliza `task_type`, define `response_style`, `requires_structured_response`, `criticality`, `allow_mock` e warnings para task desconhecida.
