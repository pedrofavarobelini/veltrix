# Prompt Builder

> Nota DOCFIX: este documento nasceu como planejamento. Em `v7.0.0`, o módulo existe em `apps/api/app/modules/prompt_builder/`. Use [[../00_MAPEAMENTO_GERAL_PEDROCORE]] para o estado atual completo.

## Responsabilidade atual

O Prompt Builder é responsável por montar o prompt final enviado ao provider, combinando:

- `system_prompt` (base ou customizado pelo sistema de origem).
- `task_type` (e a estratégia definida pelo Task Router para essa tarefa).
- `project_context` (metadados do projeto/sistema de origem, ver `PROJECT_CONTEXT.md`).
- `artifacts` (conteúdo de artefatos recebidos, quando aplicável).
- `provider`/`model` selecionados (para ajustar o prompt a peculiaridades do provider, se necessário).
- Formato de resposta esperado (`free_text` ou `structured`, e o schema correspondente quando estruturado).
- Regras de segurança (ex.: nunca instruir o provider a "executar" nada, apenas diagnosticar/sugerir — reforço da Decisão Técnica sobre QA Intelligence não executar comandos).
- Restrições específicas por tipo de tarefa (ex.: tarefas de QA devem instruir o provider a produzir os campos do schema estruturado; tarefas de chat comum não precisam dessas instruções).

## Regra importante

**O prompt não deve ficar espalhado dentro dos providers.** Hoje, `BaseAIProvider.build_prompt` já centraliza parte disso, mas de forma simples (só por `mode`). A visão-alvo é que toda a lógica de montagem de prompt — incluindo tarefa, contexto de projeto, artefatos e formato de resposta — fique em um único lugar (o Prompt Builder), e que os providers apenas recebam o prompt já pronto e o executem.

Resumindo a divisão de responsabilidades: **Task Router decide, Prompt Builder monta, Provider executa.**

## Estado de implementação

Implementado em `apps/api/app/modules/prompt_builder/`. Ele monta `enriched_system_prompt` com sistema, tarefa, origem, limites do projeto, contexto, metadata, artefatos e regras de segurança. `BaseAIProvider.build_prompt` permanece como suporte legado dos providers.
