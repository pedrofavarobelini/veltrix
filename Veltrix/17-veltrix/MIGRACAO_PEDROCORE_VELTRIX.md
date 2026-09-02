# Migração PedroCore → Veltrix

Mapa: [[MOC_VELTRIX]].
Estado final: [[17-veltrix/VELTRIX_FINAL_STATE]].
Plataforma: [[16-plataforma/PLATFORM_EVOLUTION_FINAL_STATE]].

O produto passou a se chamar **Veltrix**. Este documento existe para responder
uma pergunta específica: **o que quebrou?**

A resposta curta é **nada**. A longa está abaixo.

## 1. A regra que guiou o rename

Um replace cego teria trocado 380 arquivos e quebrado seis contratos
congelados, cinco consumidores e um schema inteiro. A regra foi outra:

| forma | o que é | decisão |
|---|---|---|
| `PedroCore`, `PedroCore IA` | nome do **produto** | → `Veltrix` |
| `pedrocore` minúsculo | **identificador técnico** | preservado |

O corte por caixa não é estético. Todo identificador técnico do projeto usa
minúscula — tabela `pedrocore_*`, contrato `pedrocore-risk-request/v1`,
`project_id="pedrocore"` — e `PEDROCORE_*` maiúsculo é variável de ambiente,
tratada à parte com alias. Separar marca de protocolo por caixa dispensou uma
lista de exceções que alguém esqueceria de atualizar.

## 2. O que mudou

- Nome do produto em README, documentação, frontend, CLI e TUI.
- Comando canônico: `veltrix`.
- Cabeçalhos HTTP canônicos: `X-Veltrix-*`.
- Variáveis canônicas: `VELTRIX_*`.
- Pacotes: `veltrix-api`, `veltrix-web`.
- Pasta de documentação: `PedroCore IA/` → `Veltrix/`.

## 3. O que **não** mudou, e por quê

### Identificadores de contrato — congelados

```text
pedrocore-integration/v1     pedrocore-capability-manifest/v1
pedrocore-quality-evidence/v1  pedrocore-execution-outcome/v1
pedrocore-learning-source/v1   pedrocore-risk-request/v1
```

Trocá-los mudaria o fingerprint congelado e quebraria todo consumidor que já
envia o nome antigo. **Identificador de protocolo não é marca**: é contrato
publicado, e contrato publicado não se renomeia porque a empresa mudou de nome.

Identificador novo só com versão nova e caminho de migração.

### Docstrings dos modelos de contrato — preservadas

Menos óbvio, e descoberto do jeito difícil: a docstring de um modelo Pydantic
vira `description` no `model_json_schema()`, **e portanto entra no
fingerprint**.

Durante o rename, o replace de prosa alterou essas docstrings e derrubou os
seis fingerprints de uma vez. Foram revertidas, e a regra ficou registrada em
`universal_contracts/versioning.py` para não se perder.

### Tabelas do banco — preservadas

Todo o schema usa o prefixo `pedrocore_`, inclusive as tabelas novas da
migration `0011`. Criar **uma** tabela com outro prefixo deixaria duas
convenções convivendo no mesmo banco, e renomear as antigas exigiria migration
destrutiva. **Branding não justifica migration destrutiva.**

### `project_id="pedrocore"` — preservado

É a identidade de um consumidor registrado no Capability Manifest, não o nome
do produto. Renomeá-lo invalidaria histórico de risco, evidência e avaliação
já gravados sob essa chave.

### Chave de armazenamento do navegador — preservada

`pedrocore-welcome-message`. Renomeá-la faria a mensagem de boas-vindas
reaparecer para todo mundo, sem nenhum ganho.

## 4. Camadas de compatibilidade

### Comando

```bash
veltrix risk        # canônico
pedrocore risk      # legado, mesmo ponto de entrada
```

Os dois apontam para a mesma função. Não há duas implementações a manter.

### Variáveis de ambiente

```text
VELTRIX_*      canônico
PEDROCORE_*    legado, ainda aceito
```

Regra em `app/core/env_compat.py`:

- só uma definida → ela vale;
- as duas com o **mesmo** valor → tudo bem, é o estado normal de quem migra aos poucos;
- as duas com valores **diferentes** → **recusa**, e não escolha silenciosa.

Escolher em silêncio seria decidir por quem configurou, e numa variável de
persistência ou de segurança a escolha errada é invisível até o incidente. A
mensagem de erro nomeia as variáveis e **nunca** mostra os valores — mensagem
de configuração é lida em log, e log é onde segredo vaza.

### Cabeçalho de credencial

```text
X-Veltrix-Api-Key      canônico
X-PedroCore-Api-Key    legado, ainda aceito
```

Os dois com valores diferentes → recusa. Preferir um em silêncio faria uma
credencial revogada continuar valendo por vir no outro nome.

**Este alias quebrou uma vez durante o próprio rename.** Um replace de prosa
atingiu o literal do cabeçalho legado e o deixou idêntico ao canônico: o alias
continuou existindo no código e parou de existir na prática. 373 testes caíram
de uma vez, todos com `401` — sintoma que parece problema de credencial e não
de rename. Existe hoje um teste que compara os dois literais e falha se
voltarem a coincidir.

## 5. O que um consumidor precisa fazer

**Nada, agora.** Tudo o que funcionava continua funcionando.

Quando quiser migrar, na ordem que preferir:

1. trocar `X-PedroCore-Api-Key` por `X-Veltrix-Api-Key`;
2. trocar `PEDROCORE_*` por `VELTRIX_*` — uma de cada vez, sem deixar as duas
   com valores diferentes;
3. trocar o comando `pedrocore` por `veltrix` em scripts;
4. adotar o Consumer SDK (`veltrix-api`), que já envia os cabeçalhos canônicos.

Os identificadores de contrato **não** entram nessa lista: eles não mudam.

## 6. Consumidores

FinGuard, Structa, Elyra, RIVVO e OrlaByte **não foram migrados** — é frente
própria. O que existe hoje para eles:

- **Consumer SDK** oficial, tipado e neutro;
- **Compatibility Matrix** (`POST /api/compatibility/check`) para responder
  "posso usar esta capability com estas versões?";
- **Capability Manifest** como fonte da verdade do que cada um declara.

Onboarding recomendado: consultar a matriz, adotar o SDK, migrar cabeçalho e
variáveis, e só então retirar o alias legado.

Nenhuma lógica específica de consumidor entrou no core — verificado por testes
que analisam a AST do SDK, do Policy Engine e da matriz.
