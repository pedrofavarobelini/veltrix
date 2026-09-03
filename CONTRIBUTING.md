# Contribuindo com o Veltrix

Este projeto tem algumas invariantes que **não são preferências de estilo**.
Elas são verificadas por teste, e um PR que as viole quebra o build. Este
documento existe para que isso não seja surpresa.

## Ambiente

```bash
cd apps/api
uv sync            # cria .venv e instala a partir do uv.lock

veltrix risk             # Risk Console (TUI)
veltrix control-center   # retrato operacional, somente leitura
# `pedrocore` continua funcionando como alias legado do mesmo comando.
```

O projeto usa [uv](https://docs.astral.sh/uv/) e declara as dependências de
desenvolvimento em `[dependency-groups]` (PEP 735). **Não use
`pip install -e ".[dev]"`**: esse extra não existe, o pip apenas avisa
`does not provide the extra 'dev'` e segue sem instalar `pytest` nem `ruff`.
Era exatamente esse comando que a CI executava, e por isso ela falhava no lint
antes de chegar aos testes.

Para rodar qualquer comando dentro do ambiente:

```bash
uv run python -m pytest -q
```

Frontend:

```bash
cd apps/web
npm install
```

## Verificação completa

Rode isto antes de abrir um PR. São os mesmos comandos da CI:

```bash
cd apps/api
uv run python -m pytest -q          # tudo verde, skips apenas nas duas categorias abaixo
uv run python -m ruff check .       # All checks passed!

cd ../web
npm run build                                  # tsc -b && vite build
```

### Os skips esperados

Não decore um número — ele envelhece a cada teste novo, e esta seção já
prometeu 21 quando a suíte tinha 30 e 30 quando tinha 62. O que é estável é a
**taxonomia**: todo skip pertence a uma destas duas categorias, e nenhuma
outra é aceita.

| Categoria | Como sair do skip | Por que existe |
|---|---|---|
| **Integração PostgreSQL** | defina `PEDROCORE_TEST_POSTGRES_URL` apontando para um banco de teste descartável | são testes de durabilidade real; um `PASS` sem banco não provaria nada |
| **Recurso real opt-in** | defina o `PEDROCORE_RUN_REAL_*` correspondente | fazem chamada externa de verdade; default `false` para que a suíte nunca gaste credencial sozinha |

Com um PostgreSQL de teste configurado, a primeira categoria some inteira e
sobram apenas os opt-in de recurso real.

Um skip **fora** dessas duas categorias é um teste que parou de rodar sem
ninguém decidir isso. `tests/conftest.py` falha a sessão quando isso acontece,
em vez de deixar o skip novo passar despercebido no meio dos legítimos — então
o guard, e não esta tabela, é a fonte de verdade.

## As quatro invariantes

### 1. Todo módulo declara seu plano

O Veltrix é um **modular monolith** com dois planos declarados:

```text
Runtime Plane  ──── evidência / contratos ────►  Learning Plane
```

Um módulo novo em `app/modules/` precisa de uma entrada em
`app/architecture/planes.py`. Sem ela, `test_control_plane_boundaries.py`
falha.

**A direção da dependência é vigiada.** O Learning Plane pode ler o Runtime
Plane — é assim que ele aprende. O contrário exige uma exceção nominal e
justificada em `RUNTIME_TO_LEARNING_EXCEPTIONS`. A lista é curta de propósito:
quando não couber em uma tela, a regra virou decoração.

### 2. Nome de projeto vive no registro, nunca no motor

Isto falha o build:

```python
if caller.project_id == "finguard":   # ❌ no core genérico
```

Isto é o caminho correto:

```python
if has_trait(caller.project_id, ProducerTrait.EXTERNALLY_OWNED):   # ✅
```

O nome do consumidor pode aparecer em `project_context/manifests.py` (o
registro) e nos módulos `elyra_*` (Consumer Capabilities). Nunca na
orquestração, no prompt builder ou em qualquer módulo genérico.

Motivo prático: antes, habilitar um comportamento para um consumidor novo
exigia editar um arquivo de 2.900 linhas no coração do Runtime Plane. Agora
exige uma linha na tabela de manifests.

### 3. Contratos V1 estão congelados

`tests/test_contract_freeze.py` compara um fingerprint SHA-256 do JSON Schema
de cada contrato V1. Mudou a forma → build quebra.

Se a mudança for legítima:

| Classe | O que fazer |
|---|---|
| **aditiva** (campo opcional com default, valor novo em enum) | atualize o fingerprint em `FROZEN_V1_SCHEMAS` e **explique o motivo no commit** |
| **breaking** (campo obrigatório, remoção, mudança de tipo ou semântica) | crie a `/v2`. A v1 permanece até existir migration path. **Nunca altere a v1 no lugar.** |

A atualização manual é o ponto: ela obriga a decisão consciente. Um contrato
publicado deixa de pertencer a quem o escreveu — quebrá-lo quebra código de
terceiro, e a falha aparece na produção *dele*.

### 4. O consumidor não emite julgamento

O Veltrix recebe **fato observado** e produz **julgamento**. Um payload que
traga `eligibility`, `authorized`, `training_candidate`, `quality_score`,
`readiness` ou `automatic_collection` é recusado inteiro.

Se você precisa transportar uma afirmação do produtor, use o prefixo que a
marca como alegação: `observed_*`, `reported_*`, `producer_asserted_*`.

```text
producer_asserted_outcome   ✅  alegação
eligibility                 ❌  sentença
```

## Estilo de código

- **Pydantic é mecanismo, não documentação.** Se uma regra importa, expresse-a
  no tipo. `Literal[False]` faz o validador recusar; `bool = False` só pede
  educadamente. Use `extra="forbid"` em todo contrato.
- **Fail-closed.** Ausência, ambiguidade ou erro nunca resultam em permissão.
  Recusar é resposta legítima; fallback silencioso não é.
- **Nunca ecoe o valor recusado** em mensagem de erro, log ou relatório.
- **Comentários explicam o porquê, não o quê.** O código já diz o que faz. O
  comentário deve dizer por que essa escolha e não a óbvia.
- **Ruff com `line-length = 100`.** Rode `ruff check .` antes do commit.

## Testes

Todo comportamento novo precisa de teste. Além disso:

**Teste o caminho desonesto.** A maior parte dos testes deste projeto não
verifica que o caminho feliz funciona — verifica que o caminho errado falha.

**Verifique seu guarda por mutação.** Depois de escrever um teste de proteção,
quebre de propósito a coisa que ele protege e confirme que ele reclama. Se não
reclamar, ele não protege nada. Restaure em seguida.

**Cuidado com estado global.** Um teste que mexe em `sys.modules`, variáveis de
ambiente ou singletons precisa de isolamento — `monkeypatch`, fixture com
teardown ou subprocesso. Um teste que passa isolado e quebra em suíte custa
mais caro do que o bug que ele pegaria.

## Documentação

O vault em `Veltrix/` é validado por
`app/modules/docs_graph` e a validação é **estrutural**: todo documento precisa
ser alcançável a partir do MOC raiz, ter ao menos um backlink e ao menos um
link de saída. Basename duplicado e link quebrado também falham.

Se você adicionar um documento, ligue-o a partir de um MOC existente e faça-o
apontar para algo. Documento órfão quebra o build.

## Commits

Prefixo convencional (`feat`, `fix`, `refactor`, `test`, `docs`, `chore`) com
escopo. O corpo deve explicar **por que**, não só o que — especialmente quando
a mudança envolve uma das quatro invariantes acima.

## O que não fazer sem conversar antes

- afrouxar uma invariante para fazer um teste passar;
- adicionar exceção em `RUNTIME_TO_LEARNING_EXCEPTIONS` por conveniência;
- fabricar população de treino para sair de `DATASET_NOT_READY` — esse estado
  é um gate funcionando, não uma pendência;
- baixar threshold de readiness ou de promoção para obter um resultado verde.
