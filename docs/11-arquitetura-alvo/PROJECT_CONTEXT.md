# Project Context (Planejado)

> Parte da frente `PEDROCORE-REPLAN-01C`. O Project Context aqui descrito é um módulo/conceito **planejado**. Ele não existe no código hoje — não há registro, arquivo de configuração ou estrutura de dados de "projeto" no PedroCore. Nenhum registro real de projeto (incluindo o FinGuard) é criado nesta etapa. Este documento apenas planeja o conceito.

## Responsabilidade futura

O Project Context seria a camada conceitual que:

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

Isso é planejamento conceitual. **Nenhum registro real de projeto é criado nesta etapa** — não há arquivo de configuração, banco de dados ou estrutura em memória representando o FinGuard ou qualquer outro sistema dentro do PedroCore hoje. O exemplo acima é ilustrativo, para orientar o desenho técnico de uma fase futura de implementação.

## Estado de implementação

Nenhuma parte do Project Context está implementada. O `ChatService`/`ProviderRegistry` atuais não têm nenhum conceito de "projeto de origem", "sistema externo" ou "limites por projeto" — isso é inteiramente uma proposta de arquitetura-alvo desta fase.
