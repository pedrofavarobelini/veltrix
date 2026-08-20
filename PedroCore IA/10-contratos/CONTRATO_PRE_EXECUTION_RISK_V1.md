# Contrato — Pre-Execution Risk Analysis V1

## Endpoint

`POST /api/risk/analyze` reutiliza o `RiskRequest` autenticado da fundação e
produz `PreExecutionRiskAnalysis`. A policy é `pre-execution-risk-v1`.

## Pipeline

`Intent → Context → Prompt Quality → Ambiguity → Scope → Rules → Semantic Catalog → Operational Memory → Historical Evidence → Blast Radius → Simulations → Dimensions`

Regras determinísticas cobrem inicialmente migration, schema, auth/authz,
secrets/.env, CI/CD, delete, mudança massiva, security policy, production,
permissions e integrações externas. A análise semântica é um catálogo local e
versionado, sem chamada a LLM.

## Saída

A análise registra separadamente:

- signals, findings e evidence;
- regras e versões acionadas;
- evidência histórica limitada da Operational Memory existente;
- blast radius por files, modules, database, users, permissions, environment,
  external integrations e security boundaries;
- seis simulações analíticas;
- `scope_risk`, `data_risk`, `security_risk`, `migration_risk`,
  `regression_risk` e `operational_risk`;
- confidence, uncertainty e policy version.

Não existe score único que esconda as dimensões.

## Segurança

Simulações são `analytical_dry_run`. Nenhuma operação perigosa é disparada,
nenhum provider é chamado e nenhuma memória paralela é criada. Falha ao
consultar persistência fecha a API com erro sanitizado.

## Navegação

- [[PRE_EXECUTION_RISK_V1]]
