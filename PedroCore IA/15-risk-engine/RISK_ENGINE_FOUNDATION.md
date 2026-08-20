# Risk Engine Foundation

O Motor de Risco é um bounded subsystem do PedroCore:

- PedroCore continua responsável por inteligência, contexto e memória;
- QA continua responsável por evidência;
- Agent continua responsável por execução;
- Risk Engine somente analisa e governa risco.

## Pipeline inicial

`RiskRequest → Intent → Resolved Context → Prompt Quality → Ambiguity → Scope → Signals → Findings`

Os cinco analisadores são determinísticos e não chamam provider. A operação
estruturada é confrontada com a operação inferida do texto; divergência vira
sinal explícito. Contexto ausente aumenta incerteza, e escopo proibido não é
tratado como simples alvo desconhecido.

Não existem persistência, provider routing, segunda memória, learning próprio
ou execução de comandos neste módulo.

## Navegação

- [[CONTRATO_RISK_ENGINE_FOUNDATION]]
- [[SAFE_REUSE_FOUNDATION]]
- [[PRE_EXECUTION_RISK_V1]]
