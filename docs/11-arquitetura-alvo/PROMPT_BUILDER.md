# Prompt Builder (Planejado)

> Parte da frente `PEDROCORE-REPLAN-01C`. O Prompt Builder aqui descrito é um módulo **conceitual/planejado**. Ele não existe no código hoje. Hoje, cada provider monta seu próprio prompt via `BaseAIProvider.build_prompt` (`apps/api/app/modules/providers/base.py`), um template fixo por `mode`. Este documento planeja centralizar essa responsabilidade em um módulo dedicado, sem implementar nada nesta etapa.

## Responsabilidade futura

O Prompt Builder seria responsável por montar o prompt final enviado ao provider, combinando:

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

Nenhuma parte do Prompt Builder dedicado está implementada. O que existe hoje é o método `build_prompt` dentro de `BaseAIProvider`, compartilhado por todos os providers, mas limitado a `system_prompt` + `mode` + `message` — sem suporte a `task_type`, `context`, `artifacts` ou formato de resposta estruturado. A evolução para um Prompt Builder dedicado e mais robusto é planejamento desta fase, não implementação.
