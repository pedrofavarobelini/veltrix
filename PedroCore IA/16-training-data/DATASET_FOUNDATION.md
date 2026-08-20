# Dataset Foundation

Estado: **IMPLEMENTED**. Policy: `dataset-foundation-v1`.

A fundação separa três conceitos:

`Operational Learning ≠ Training Candidate ≠ Neural Training`

Operational Memory continua sendo a memória operacional autoritativa. Um
Training Candidate é somente uma projeção derivada, com provenance e
autorização. Nesta etapa não existe persistência de dataset, download de modelo,
tokenização ou treinamento.

## Fluxo

`Evidence → explicit data-use authorization → provenance gate → privacy/exclusion gate → eligible candidate`

O ID é um fingerprint determinístico do conteúdo estruturado e das evidências,
sem depender dos timestamps. Isso prepara deduplicação futura sem copiar
conversas completas.

## Exclusões fail-closed

- provenance ausente, desconhecida, duplicada ou não verificada;
- projeto divergente;
- uso neural não autorizado;
- conversa/prompt/resposta brutos;
- secrets, credenciais, `.env`, PII e dados financeiros pessoais;
- conteúdo restrito ou confidencial sem aprovação específica;
- payload acima do limite.

## Navegação

- [[CONTRATO_TRAINING_DATA_CANDIDATE]]
- [[HISTORICAL_RISK_INTELLIGENCE]]
