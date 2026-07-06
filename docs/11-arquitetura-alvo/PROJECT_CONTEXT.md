# Project Context

> Nota DOCFIX: este documento nasceu como planejamento. Em `v7.0.0`, o módulo existe em `apps/api/app/modules/project_context/`. Use [[../00_MAPEAMENTO_GERAL_PEDROCORE]] para o estado atual completo.

## Responsabilidade atual

O Project Context é a camada que:

- Representa sistemas externos do ecossistema Pedro (ex.: FinGuard) como entidades configuráveis dentro do PedroCore.
- Armazena metadados planejados sobre o sistema de origem (nome de exibição, identificador, tipo de projeto).
- Define os limites do que o PedroCore pode ou não fazer em relação àquele projeto (ex.: quais `task_type` são permitidos, se é somente leitura, se pode ou não "sugerir comandos").
- Guarda configurações planejadas por projeto (ex.: preferências de provider, nível de rigor esperado nas respostas).
- Registra explicitamente que o FinGuard é externo e somente leitura.
- Impede acoplamento direto com o código do FinGuard — o Project Context é uma representação **dentro do PedroCore**, nunca uma referência ao repositório ou banco de dados do FinGuard.

## Campos conceituais (exemplo ilustrativo)

```json
{
  "project_id": "finguard",
  "display_name": "FinGuard",
  "allowed_tasks": ["qa_report_analysis", "artifact_summary", "technical_explanation"],
  "read_only": true,
  "can_execute_commands": false,
  "can_write_files": false
}
```

Campos ilustrados:

- `project_id` — identificador único do sistema de origem, correspondente ao `origin_system` do contrato de orquestração.
- `display_name` — nome legível do projeto, para uso em logs/auditoria futura.
- `allowed_tasks` — lista de `task_type` que aquele sistema de origem está autorizado a solicitar.
- `read_only` — reforça, no nível de configuração, que o PedroCore nunca escreve de volta no sistema de origem.
- `can_execute_commands` — sempre `false` para o FinGuard e, previsivelmente, para qualquer sistema externo nesta arquitetura — o PedroCore nunca executa comandos em projetos externos (ver `suggested_commands` em `docs/10-contratos/CONTRATO_QA_INTELLIGENCE.md`, que são apenas sugestões textuais).
- `can_write_files` — sempre `false` para o FinGuard nesta arquitetura — reforça a regra de somente leitura.

## Deixar claro

O contexto atual é configuração interna em memória, não banco de dados e não leitura de repositórios externos. `finguard` e `finguard-local` são representações internas seguras; não apontam para path real do FinGuard.

## Estado de implementação

Implementado em `apps/api/app/modules/project_context/`. Resolve `pedrocore`, `finguard`, `finguard-local` e `unknown`; avalia `allowed_tasks`; mantém FinGuard read-only e sem execução/escrita.
