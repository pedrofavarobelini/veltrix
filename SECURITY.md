# Política de Segurança

## Como reportar uma vulnerabilidade

Use o **private vulnerability reporting** do GitHub neste repositório
(aba *Security* → *Report a vulnerability*). Ele cria um canal privado entre
quem reporta e o mantenedor.

**Não abra issue pública** para vulnerabilidade. Uma issue é indexada antes de
existir correção, e o relato vira instrução de exploração.

Ao reportar, ajuda muito incluir: o que acontece, o que deveria acontecer, e o
menor caminho para reproduzir. **Não inclua segredo real** — descreva o tipo e
a localização.

## Postura de segurança do projeto

O PedroCore é **fail-closed por padrão**. Tudo o que pode causar dano, custo ou
vazamento está desligado até alguém ligar explicitamente:

| Recurso | Default |
|---|---|
| Provider real (Gemini, OpenAI, Claude, Grok, DeepSeek) | **desligado** — o default é mock |
| Fallback real entre providers | **desligado** |
| Persistência operacional e Evidence Registry | **desligado** |
| Leitura de artefatos do disco | **desligado** |
| OCR, multimodal, Playwright | **desligados** |
| Observabilidade técnica | **desligada**, bloqueada em produção |
| Roteamento por política | modo `legacy` |
| Coleta automática de dados de treino | **impossível por tipo** (ver abaixo) |

## Invariantes que não são configuráveis

Alguns comportamentos não são flags — são tipos. Alterá-los exige mudar o
código-fonte e passar por revisão, e não existe variável de ambiente, payload
ou configuração capaz de contorná-los:

- **`automatic_collection` é `Literal[False]`.** O validador *recusa* o valor
  `True`. O PedroCore nunca varre fontes por conta própria em busca de dados de
  treino; toda seleção é um ato explícito de um administrador.
- **`derived_content_only` é `Literal[True]`** no contrato de fonte de
  aprendizado. Conteúdo bruto — transcrição, diário, mídia, log integral — não
  entra por esse caminho em nenhuma circunstância.
- **Um consumidor não pode emitir julgamento.** Campos como `eligibility`,
  `authorized`, `training_candidate`, `quality_score` e `readiness` são
  reservados ao servidor. Um payload que os traga — em qualquer profundidade e
  qualquer grafia — é **recusado inteiro**, e não silenciosamente limpo.

## Tratamento de dados sensíveis

- Toda evidência recebida passa por varredura de segredo, credencial, token,
  PII, dado financeiro, caminho pessoal e conteúdo bruto **antes de qualquer
  escrita**. Um segredo gravado já vazou, mesmo que apagado em seguida.
- Achados reportam **código, categoria e caminho do campo — nunca o valor
  detectado**. Devolver o trecho colocaria o segredo no log, na resposta de
  erro e no relatório de auditoria.
- Mensagens de erro de contrato **não ecoam o payload recusado**.
- Mensagens de bloqueio não nomeiam consumidores específicos: um aviso que
  nomeia um sistema revela a terceiros quais o PedroCore conhece.

## Isolamento entre projetos

O isolamento por projeto é **chave primária no banco**, não filtro de
aplicação. Um erro de query não consegue atravessar a fronteira entre
consumidores.

Credenciais são resolvidas no servidor. O `project_id` que chega no payload é
apenas **conferido** contra a credencial autenticada — divergência é recusa.

## Segredos no repositório

Nenhum segredo real é versionado. O único arquivo de ambiente rastreado é
`apps/api/.env.example`, com todos os campos de chave vazios. `.gitignore`
cobre `.env`, `.env.*` e artefatos de treinamento (`*.safetensors`, `*.ckpt`,
`pytorch_model*.bin`, diretórios de dataset e checkpoints).

Se você encontrar um segredo versionado, trate como vulnerabilidade e use o
canal privado acima.
