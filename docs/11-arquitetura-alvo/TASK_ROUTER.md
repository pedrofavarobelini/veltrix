# Task Router (Planejado)

> Parte da frente `PEDROCORE-REPLAN-01C`. O Task Router aqui descrito é um módulo **conceitual/planejado**. Ele não existe no código hoje — não há classe, função ou arquivo `task_router` em `apps/api`. Este documento orienta o desenho futuro, sem implementar nada nesta etapa.

## Responsabilidade futura

O Task Router seria o primeiro módulo a processar uma requisição de orquestração (ver `docs/10-contratos/CONTRATO_ORQUESTRACAO.md`), responsável por:

- Receber o `task_type` da requisição.
- Interpretar o `origin_system` (e o `source`, se presente) para aplicar regras específicas por sistema chamador.
- Identificar a natureza da tarefa: chat comum, explicação técnica, análise de QA, análise de log, revisão de roadmap, etc.
- Decidir a **estratégia de resposta**: se a resposta pode ser texto livre ou precisa ser estruturada (ver `docs/10-contratos/CONTRATO_ORQUESTRACAO.md`, seção 3, e `CONTRATO_QA_INTELLIGENCE.md`).
- Indicar se o `MockProvider` pode ser usado para aquela tarefa ou se um provider real é recomendado/obrigatório.
- Acionar o Prompt Builder já com a estratégia definida (tipo de tarefa, formato de resposta esperado, nível de criticidade).

## Regra de responsabilidade

**Task Router decide. Prompt Builder monta. Provider executa.** O Task Router nunca monta prompt final nem chama provider diretamente — ele apenas decide a estratégia e repassa para o Prompt Builder.

## Exemplos de roteamento planejado

| `task_type` | Formato de resposta | Uso de Mock | Provider real |
|---|---|---|---|
| `general_chat` | Livre | Permitido, sem restrição | Não exigido |
| `technical_explanation` | Livre ou semi-estruturada | Permitido em desenvolvimento | Recomendado em uso real, não obrigatório |
| `qa_report_analysis` | Estruturada (obrigatória) | Não confiável para validação crítica — apenas para teste de integração | Obrigatório para análise real (Decisão Técnica 020) |
| `release_gate_review` | Estruturada (obrigatória) | Fallback para Mock deve **bloquear a conclusão** da tarefa, não gerar uma resposta como se fosse válida | Obrigatório, dado o caráter crítico |
| `visual_qa_analysis` | Estruturada (obrigatória) | Apenas para teste de integração | Obrigatório, e exige suporte a imagem/evidência visual — capacidade ainda não definida tecnicamente (fase futura) |

Os demais `task_type` especificados em `docs/10-contratos/CONTRATO_ORQUESTRACAO.md` (`code_help`, `project_context_answer`, `qa_failure_diagnosis`, `log_analysis`, `roadmap_review`, `artifact_summary`) seguem o mesmo princípio: tarefas de uso geral/exploração toleram Mock e resposta livre; tarefas de QA/decisão crítica exigem resposta estruturada e provider real.

## Estado de implementação

Nenhuma parte do Task Router está implementada. Não há classificação automática de tarefa, não há lógica de decisão de estratégia e não há acionamento de Prompt Builder no código hoje — o `ChatService` atual apenas recebe `provider`/`mode` diretamente do payload e não interpreta `task_type` nem `origin_system`, pois esses campos não existem no contrato atual.
