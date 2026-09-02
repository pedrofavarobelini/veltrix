# Risk Console — guia de uso

Mapa da frente: [[MOC_ARQUITETURA]].
Fechamento do motor: [[RISK_ENGINE_V2_BASELINE]].
Documentação V1: [[RISK_ENGINE_FOUNDATION]], [[PRE_EXECUTION_RISK_V1]],
[[EXECUTION_CONTRACT_RISK_GATES]], [[POST_EXECUTION_QA]],
[[HISTORICAL_RISK_INTELLIGENCE]].

Este documento é para quem vai **usar** o Risk Console — alguém técnico que não
conhece a implementação por dentro. Ele não repete a arquitetura do motor; para
isso, [[RISK_ENGINE_V2_BASELINE]].

## 1. O que é

Uma interface local para responder uma pergunta antes de executar um prompt:
**o que acontece se isto rodar?**

Ela existe em duas formas, sobre o mesmo motor:

| forma | para quem |
|---|---|
| TUI (console de terminal) | humano decidindo na hora |
| CLI | script, pipeline, uso em lote |

A interface principal do PedroCore (SPA React) **não foi alterada** por esta
frente. O Risk Console é separado de propósito: o público dele é outro, e a UI
principal está congelada.

## 2. Instalação

Pré-requisitos: Python 3.11+ e [uv](https://docs.astral.sh/uv/).

```bash
cd apps/api
uv sync
```

`uv sync` instala o grupo `dev`, que já inclui o extra `console`. Quem quiser
só o console, sem o ferramental de teste:

```bash
uv sync --extra console
```

### Dependências

O console acrescenta **uma** dependência direta: `textual` (que traz `rich` e
`platformdirs`). Ela é declarada em `[project.optional-dependencies].console` —
o container da API não precisa de TUI, e por isso ela não entra nas
dependências obrigatórias do servidor.

A CLI não acrescenta nada: usa `argparse`, da biblioteca padrão.

## 3. Como abrir

```bash
pedrocore risk
```

É só isso. **Não é preciso subir `uvicorn` nem o frontend.** O console fala com
o core no mesmo processo — a porta HTTP continua existindo e é o caminho de
consumidor externo, não o do humano no terminal.

Se o comando não for encontrado, o ambiente não foi sincronizado; rode
`uv sync` em `apps/api` e tente de novo.

## 4. A tela

Em terminal largo, um painel de duas colunas:

```text
 VELTRIX RISK ENGINE                    Console de Risco Pré-Execução
╭─ ENTRADA ──────────────╮ ╭─ ANÁLISE DE RISCO ──╮ ╭─ RAIO DE IMPACTO ─╮
│ Projeto                │ │ Intenção            │ │ Arquivos          │
│ Ambiente               │ │ Modifica            │ │ Módulos           │
│ Executor               │ │ Qualidade           │ │ Amplitude         │
│ Prompt                 │ │ Ambiguidade         │ │ Extensão          │
│                        │ │ Confiança           │ │ Magnitude         │
│ ▶ CONFIGURAÇÕES AVANÇ. │ ╰─────────────────────╯ ╰───────────────────╯
│    ANALISAR RISCO      │ ╭─ DIMENSÕES DE RISCO ────────────────────╮
╰────────────────────────╯ ╰─────────────────────────────────────────╯
┏━ GATE FINAL ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                     REVISÃO OBRIGATÓRIA                           ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
╭─ CENÁRIOS ────╮ ╭─ HISTÓRICO ──╮ ╭─ ACHADOS ───╮ ╭─ RECOMENDAÇÕES ─╮
▶ DETALHES TÉCNICOS
 EDITAR PROMPT  REANALISAR  EMITIR CONTRATO  COPIAR PROMPT  EXPORTAR  SAIR
```

O **Gate Final** fica acima dos painéis de detalhe, e não no fim. É a
resposta que se procura ao abrir a ferramenta; enterrá-la depois de vários
cenários faria o console responder por último a pergunta que veio primeiro.

Em terminal estreito (menos de 100 colunas) as duas colunas viram uma, os
painéis empilham e a barra de ações vira uma grade de dois níveis. Nada
desaparece.

### Projeto

Lista derivada do **Capability Manifest**: aparecem os projetos que declaram a
capability `risk_analysis`. O console não tem lista fixa de projetos e não sabe
o nome de nenhum em particular — um projeto novo aparece por declarar o que faz.

### Ambiente

`Desenvolvimento` · `Teste` · `Produção`

Rótulo humano na tela, valor canônico no motor. `Produção` importa: as regras
determinísticas tratam alteração de segredo em produção como bloqueio.

### Executor

`Claude Code` · `Codex` · `Agente genérico` · `Manual`

Nesta versão o executor é **contexto, não ação**. Ele viaja para a análise e
para o contrato, e muda o resultado — mas **nenhum agente é invocado**. O
console não executa nada.

### Prompt

Área multilinha, até o limite do Risk Engine (4000 caracteres). Um prompt maior
é **recusado com a contagem**, e não cortado em silêncio: truncar mudaria o que
foi analisado sem você saber.

### Configurações avançadas

Recolhidas ao abrir. Dentro delas: `Operação` (opcional — o Veltrix identifica
pelo prompt se você não informar), `Permissões`, `Escopo permitido`, `Escopo
proibido`, `Alvos`, `Restrições`, `Critérios de aceitação`, `Testes exigidos`,
`Integrações externas`, `Banco de dados` e `Plano de rollback`.

Cada campo traz uma linha de ajuda em português explicando o que declarar.

Eles são opcionais **e mudam o resultado de verdade**. Vale entender o
principal: sem `Permissões` declaradas, a política responde `BLOQUEADO` por
`PERMISSION_CONFLICT` — em praticamente qualquer pedido.

Isso não é defeito. O console **não preenche permissão por você** para produzir
um resultado bonito: um pedido sem permissão declarada é, de fato, um pedido
que não deveria executar.

### Cenários e detalhes técnicos

Cada cenário é uma linha com nome e severidade; abrir mostra efeito, gatilho,
escopo afetado, contenção, rollback, verificação, risco residual e confiança.
Nada foi removido — apenas recolhido.

`DETALHES TÉCNICOS`, também recolhido, guarda reason codes, políticas,
identificadores e scores. A tela principal fala português; o código interno
fica onde serve de auditoria e não de leitura.

### Teclado

| atalho | ação |
|---|---|
| `Ctrl+R` | analisar risco |
| `Ctrl+E` | editar prompt |
| `Ctrl+D` | abrir/fechar configurações avançadas |
| `Ctrl+Q` | sair |
| `Tab` | navegar entre campos |

Mouse funciona; teclado é suficiente. Severidade e gate sempre trazem o rótulo
textual (`BAIXO`, `ALTO`, `BLOQUEADO`) além da cor — a tela continua legível em
terminal monocromático ou para quem não distingue as cores usadas.

## 5. Os gates

| interno (contrato) | na tela |
|---|---|
| `PASS` | APROVADO |
| `PASS_WITH_WARNINGS` | APROVADO COM AVISOS |
| `REVIEW_REQUIRED` | REVISÃO OBRIGATÓRIA |
| `BLOCK` | BLOQUEADO |

O enum interno **não foi traduzido**. Só a apresentação é.

### Quando dá BLOQUEADO

A tela mostra `EXECUÇÃO BLOQUEADA`, o motivo, os achados bloqueantes e as
recomendações — e **desabilita** `EMITIR CONTRATO` e `COPIAR PROMPT APROVADO`.

O botão desabilitado é conveniência. A recusa de verdade está no serviço: quem
chamar a função direto recebe a mesma recusa. A interface não contorna o
backend, e não existe caminho na tela que transforme análise em autorização.

## 6. Ações

| ação | o que faz |
|---|---|
| `ANALISAR RISCO` | roda a análise; nada é executado |
| `EDITAR PROMPT` | volta ao campo e invalida a aprovação anterior |
| `REANALISAR` | analisa de novo o formulário atual |
| `EMITIR CONTRATO` | emite o Execution Contract assinado |
| `COPIAR PROMPT APROVADO` | copia o prompt vinculado à análise vigente |
| `EXPORTAR` | grava um JSON sanitizado |
| `VER EVIDÊNCIA` | resumo da evidência histórica, quando existe |
| `SAIR` | fecha |

Atalhos: `Ctrl+R` analisa, `Ctrl+Q` sai.

### O vínculo entre prompt e análise

Se você editar qualquer campo depois de analisar, as ações de aprovação são
desabilitadas até uma nova análise. O caminho que isso impede é concreto:

```text
analisa A  ->  edita para B  ->  copia B usando a aprovação de A
```

A comparação é feita sobre a **assinatura do conteúdo analisado**, não só sobre
o texto: mudar escopo ou permissão também muda o que foi aprovado.

## 7. Contrato

`EMITIR CONTRATO` exige chave de assinatura:

```bash
export PEDROCORE_RISK_CONTRACT_SIGNING_KEY="<pelo menos 32 caracteres>"
```

Sem ela, o console diz exatamente isso — e não emite nada. Contrato sem
assinatura não é contrato.

## 8. Exportação

O JSON exportado é **sanitizado na saída**: chaves, tokens, senhas, cabeçalhos
de autorização, strings de conexão com credencial e blocos PEM viram
`[REDIGIDO]`.

A redação é conservadora de propósito: prefere marcar demais a deixar passar.
Um `[REDIGIDO]` a mais custa uma pergunta; um token a menos custa uma rotação
de credencial.

O clipboard **não é persistido**. Stack traces internos e caminhos de
configuração não aparecem em mensagem de erro.

## 9. CLI

```bash
pedrocore risk                                  # abre a TUI
pedrocore risk inspect                          # projetos, ambientes, executores
pedrocore risk analyze prompt.txt               # analisa um arquivo
cat prompt.txt | pedrocore risk analyze --stdin # analisa da entrada padrão
pedrocore risk analyze prompt.txt --json        # saída estruturada
pedrocore risk contract prompt.txt              # emite contrato, se aprovado
pedrocore risk validate-contract c.json --project <p> --producer <q>
pedrocore risk history --project <p> --producer <q> [--days 30]
pedrocore risk benchmark casos.json
```

Flags de contexto (em `analyze` e `contract`):

```text
--project  --environment  --executor  --permissions  --allowed-scope
--forbidden-scope  --targets  --required-tests  --constraints
--acceptance-criteria  --integrations  --database  --rollback-plan
--json  --output  --no-ai
```

### Códigos de saída

| código | significado |
|---|---|
| `0` | análise concluída |
| `2` | erro de entrada (arquivo, projeto, ambiente, prompt) |
| `3` | erro operacional |
| `4` | gate `BLOCK` |

`BLOCK` tem código próprio para que um pipeline reaja a "bloqueado" sem
interpretar texto. Falha de uso e falha de política são coisas diferentes.

**Nenhum subcomando executa a operação analisada.** A saída `--json` é sempre
UTF-8, inclusive quando redirecionada no Windows.

### `benchmark`

Recebe os casos por **arquivo**, e não por flag: o serviço real exige uma lista
de `BenchmarkCase`, cada um com uma `RiskRequest` completa. Isso não se deriva
de um punhado de flags, e um caso sintético produziria o benchmark de nada.

## 10. PostgreSQL de teste

Os testes de persistência ficam `skip` sem banco. Para executá-los de verdade,
com um banco **descartável** — nunca produção, nunca banco de consumidor:

```bash
docker run -d --name pedrocore-risk-test-pg \
  -e POSTGRES_PASSWORD=riskqa -e POSTGRES_USER=riskqa -e POSTGRES_DB=riskqa \
  -p 55433:5432 postgres:16-alpine

cd apps/api
export PEDROCORE_TEST_POSTGRES_URL="postgresql://riskqa:riskqa@localhost:55433/riskqa"
uv run python -m pytest -q
```

As migrations são aplicadas pelo runner já existente. Ao terminar:

```bash
docker rm -f pedrocore-risk-test-pg
```

Sem a variável, os casos permanecem `skip` — o que é honesto. Um PASS sem banco
não seria.

## 11. Problemas comuns

| sintoma | causa provável |
|---|---|
| `pedrocore: command not found` | ambiente não sincronizado — rode `uv sync` em `apps/api` |
| "precisa do pacote 'textual'" | instale com `uv sync --extra console` |
| Tudo dá `BLOQUEADO` | falta declarar `Permissões` compatíveis com a operação |
| `OPERATION_UNKNOWN` | o prompt não permite inferir a operação; declare-a no campo `Operação` |
| `EMITIR CONTRATO` recusa | gate `BLOCK`, ou `PEDROCORE_RISK_CONTRACT_SIGNING_KEY` ausente/curta |
| Acentos quebrados ao redirecionar | não deveria ocorrer: a saída é forçada para UTF-8 |
| Ações de aprovação desabilitadas | o formulário mudou; use `REANALISAR` |

## 12. Fronteiras desta frente

Registrado para que fique claro o que **não** mudou:

- A UI React principal **não foi alterada**.
- O motor de risco **não mudou**: o console consome os mesmos serviços que o
  router HTTP consome, e não tem regra de risco própria.
- O rename global PedroCore → Veltrix **não foi feito**. A tela já usa a
  identidade aprovada; variáveis de ambiente, tabelas, identificadores de
  contrato congelados e nome de pacote continuam em `pedrocore`. A marca está
  centralizada em `app/modules/risk_console/branding.py` para que o rename seja
  a edição de um módulo, e não uma caçada a `grep`.
- As 12 evoluções de plataforma e as evoluções futuras seguem documentadas em
  [[RISK_ENGINE_V2_BASELINE]] e **não implementadas**.
