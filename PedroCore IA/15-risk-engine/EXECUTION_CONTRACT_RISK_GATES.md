# Execution Contract + Risk Gates

O contrato transforma análise em restrições verificáveis sem transformar o
Risk Engine em executor. A API possui três operações separadas:

- emitir contrato a partir do RiskRequest;
- validar integridade, contexto, gate e expiração;
- registrar override humano autorizado.

## Proteções

- HMAC cobre todos os campos do contrato;
- context signature cobre todo o RiskRequest canônico;
- projeto vem da credencial registrada;
- permission conflict e forbidden scope bloqueiam;
- mass assignment de gate/assinatura é rejeitado pelo schema;
- reviewers usam allowlist separada;
- override de `BLOCK` é proibido;
- review record também é assinado e verificável.

Nenhum endpoint executa a operação alvo, comando ou provider.

## Navegação

- [[CONTRATO_EXECUTION_CONTRACT]]
- [[PRE_EXECUTION_RISK_V1]]
- [[POST_EXECUTION_QA]]
