# Historical Risk Intelligence

A inteligência histórica fecha o ciclo sem duplicar armazenamento:

`Execution Outcome V2 → Operational Memory → Historical Query → Benchmark`

## Fontes e compatibilidade

Os padrões vêm do repositório da Operational Memory e seus IDs de evidência
apontam para Report Intelligence persistido. A versão do Motor de Risco é lida
do metadata do report. Uma entrada só participa quando a policy é conhecida,
compatível e solicitada; versões diferentes nunca são agregadas em silêncio.

O histórico retorna evidência agregada, não causalidade universal. Abaixo de 30
amostras, a resposta sinaliza amostra pequena e impede a classificação como
generalizável.

## Estratégias avaliadas

- `deterministic_only`: regras locais versionadas;
- `semantic_only`: sinais do catálogo semântico local;
- `history_only`: Retrieval limitado aos IDs históricos compatíveis;
- `hybrid`: união conservadora das três fontes.

History-only pode abster-se quando não há padrão compatível. A abstenção é
mensurada como necessidade de revisão, não convertida em acerto. False negative
severo recebe o maior peso e é o primeiro critério de recomendação.

## Limites de segurança

O serviço é analítico: não executa o alvo, não chama provider, não faz
fine-tuning e não modifica a Operational Memory. A falha da persistência
operacional fecha os endpoints com erro sanitizado.

## Navegação

- [[CONTRATO_HISTORICAL_RISK]]
- [[POST_EXECUTION_QA]]
- [[PRE_EXECUTION_RISK_V1]]
- [[DATASET_FOUNDATION]]
