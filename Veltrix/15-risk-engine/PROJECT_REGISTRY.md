# Project Registry

Catálogo dos projetos que o Veltrix conhece. Identidade, e só.

Relacionado: [[RISK_CONSOLE]] · [[VELTRIX_FINAL_STATE]] · [[MOC_ARQUITETURA]]

---

## 1. O problema que ele resolve

O seletor `Projeto` do Risk Console lia a lista do **Capability Manifest**.
Isso amarrava duas coisas que não têm relação:

```text
aparecer no console   ⟵ exigia ⟶   ter manifesto escrito no código
```

O efeito prático era que só `pedrocore` aparecia. Um usuário com um projeto
próprio não tinha como analisá-lo — precisaria editar o código-fonte do Veltrix
para que o próprio projeto existisse na lista.

O registry separa as duas perguntas:

```text
Project Registry        →  que projetos existem, como se chamam, onde ficam
Capability Manifest     →  o que cada projeto declara saber fazer
Executor Profile        →  o que o agente consegue fazer
Policy Engine           →  o que é permitido fazer
```

Apenas a primeira mudou de lugar. As outras três continuam sendo a autoridade
de capacidade, e a permissão efetiva continua sendo a interseção das três.

---

## 2. O que o registry NÃO é

Este é o ponto que os testes protegem com mais cuidado:

```text
estar registrado    !=   ter capacidade
ter nome conhecido  !=   ter manifesto
editar metadata     !=   trocar de identidade
arquivar            !=   apagar
```

Criar um projeto chamado `finguard` não concede nada a ninguém. Um projeto sem
Capability Manifest continua produzindo `UNKNOWN` — que é a resposta segura —
em vez de um padrão generoso deduzido do nome.

Não há sincronização com GitHub nesta versão. `repository_url` é **metadado
exibido**: nenhuma rede é tocada, nenhum token é pedido, nenhum repositório é
clonado ou lido. Um teste vigia essa ausência lendo os imports do módulo.

---

## 3. O modelo

| campo | obrigatório | observação |
|---|---|---|
| `project_id` | sim | normalizado, único, **imutável** |
| `display_name` | sim | livre, editável |
| `local_path` | não | metadado; travessia de diretório é recusada |
| `repository_url` | não | metadado; `https/http/ssh/git@` apenas |
| `status` | sim | `ACTIVE` \| `ARCHIVED` |
| `created_at` / `updated_at` | sim | UTC |
| `capability_manifest_reference` | não | ponteiro, não conteúdo |

Oito campos. Cada campo a mais seria um fato que o registry passaria a afirmar
sobre o projeto — e afirmar sem base é o defeito que três frentes anteriores
corrigiram.

### Por que o `project_id` é imutável

Ele é a **chave de isolamento**: decide de quem é cada linha, cada análise e
cada contrato. Se pudesse ser editado depois, "editar metadata" viraria
"assumir a identidade de outro projeto".

`ProjectRegistryService.update()` não tem parâmetro capaz de alterá-lo, e há um
teste que inspeciona a assinatura para garantir que continue assim.

---

## 4. Identidade: normalização e recusa

```text
"Meu Projeto"      →  meu-projeto
"  Minha Área "    →  minha-area
"../etc/passwd"    →  RECUSADO
"a/b"              →  RECUSADO
""                 →  RECUSADO
```

Travessia de caminho é **recusada, não saneada**. Sanear produziria um id
plausível a partir de uma tentativa de travessia, e um id plausível é
exatamente o que não se quer guardar como identidade de isolamento.

A mesma regra vive no schema do banco, como `CHECK`:

```sql
project_id ~ '^[a-z0-9][a-z0-9_-]{1,62}[a-z0-9]$'
```

Duplicada de propósito: um dump reconstruído entra pelo banco, não pelo
validador Python.

---

## 5. Seeds

Seis projetos iniciais, para que a primeira abertura não mostre uma lista
vazia:

| id | nome | manifesto |
|---|---|---|
| `pedrocore` | Veltrix | sim |
| `finguard` | FinGuard | sim |
| `structa` | Structa | sim |
| `elyra` | Elyra | sim |
| `rivvo` | RIVVO | **não** |
| `orlabyte` | OrlaByte | **não** |

`pedrocore` é o identificador **histórico** do próprio produto, preservado pela
mesma regra do rename: o nome de exibição virou Veltrix, a identidade não.
Trocar a chave orfanaria o Capability Manifest, a Project Surface e todo o
histórico de análise já gravado sob ela.

RIVVO e OrlaByte não têm manifesto — e funcionam. Eles são a demonstração viva
de que ausência de manifesto não impede análise.

**Seeds são configuração, não regra.** Um teste lê o AST de
`service.py`, `repository.py`, `schemas.py`, `risk_console/domain.py`,
`risk_intake/builder.py` e `risk_engine/analyzers.py` procurando qualquer
comparação com um nome de projeto. Se algum dia aparecer um
`if project_id == "finguard"`, ele falha.

Semear nunca sobrescreve: um id que já existe fica como está. Semear é
preencher catálogo vazio, não restaurar estado de fábrica.

---

## 6. Ordem da lista

Ordem de **registro**, não alfabética — e a ordenação mora no serviço, não no
store, para que memória, JSON e PostgreSQL apresentem a mesma lista.

Alfabética elegeria como padrão do console qualquer projeto cujo nome comece
com A. Por `created_at`, os seeds ficam na ordem declarada e um projeto novo
aparece no fim, onde o usuário acabou de criá-lo — sem que nenhuma linha de
código precise saber o nome de projeto nenhum.

---

## 7. Persistência

Padrão canônico do Veltrix: `Protocol` + InMemory + LocalJson + PostgreSQL.

```text
VELTRIX_PROJECT_REGISTRY = memory | local_json | postgresql
VELTRIX_PROJECT_REGISTRY_DIR            (local_json)
VELTRIX_PROJECT_REGISTRY_DATABASE_URL   (postgresql)
```

Fail-closed: modo inválido **falha**, não vira `memory`. `postgresql` sem URL
**recusa**, não cai para memória em silêncio — perder um projeto criado sem
avisar seria perder a identidade sob a qual as análises dele foram gravadas.
Catálogo JSON corrompido nunca é lido como catálogo vazio.

Migration `0012_project_registry.sql`, **aditiva**. Nenhuma anterior foi
tocada. A tabela mantém o prefixo `pedrocore_`: o schema inteiro usa esse
prefixo, e criar uma tabela com outro deixaria duas convenções convivendo —
branding não justifica migration destrutiva.

Isolamento é **chave**, não filtro pós-leitura: `project_id` é PRIMARY KEY, e o
banco recusa uma segunda linha com a mesma identidade.

`ON CONFLICT DO UPDATE` nunca inclui `project_id` no `SET`.

---

## 8. Onboarding de um projeto novo

```text
NOVO PROJETO
    ↓
Project Registry            identidade: id, nome, caminho, repositório
    ↓
Capability Manifest         OPCIONAL — enriquece o contexto quando existe
    ↓
Risk Auto Context           resolve operação, alvo, escopo, permissões
    ↓                       o que o manifesto traria e não existe: UNKNOWN
Risk Engine                 dimensões, alcance, cenários, achados
    ↓
Risk Gate                   APROVADO / COM AVISOS / REVISÃO / BLOQUEADO
```

Cada etapa funciona sem a anterior ter sido enriquecida. O que muda sem
manifesto não é a possibilidade de analisar — é a **quantidade de fatos
conhecidos**, e os desconhecidos aparecem como `UNKNOWN` em vez de sumirem.

---

## 9. No console

```text
Projeto  [ Veltrix ▼ ]  [ + ]
         Veltrix · Manifesto: disponível · Local: não configurado
         GERENCIAR PROJETOS
```

`[+]` abre **NOVO PROJETO**: nome, id (auto-gerado e mostrado enquanto o nome é
digitado), caminho local opcional, repositório opcional.

**GERENCIAR PROJETOS** edita `display_name`, `local_path` e `repository_url`,
mostra o `project_id` e o estado do manifesto, arquiva e reativa. Não apaga —
não há `delete` no serviço, e um teste verifica que continua não havendo.

O caminho completo não fica permanentemente na tela: o badge diz apenas se está
configurado. Detalhe fica sob demanda.

---

## 10. Guarda na análise

O `build_request` exige que o projeto esteja **registrado e ativo**.

Antes a exigência era declarar `risk_analysis` no manifesto. Essa exigência
caiu — ela era o que impedia um projeto do usuário de ser analisado. O que fica
é a guarda de **identidade**: um id que o catálogo não conhece não vira projeto
por ser digitado, e um projeto arquivado não volta ao fluxo porque alguém
informou o id dele.

Um id arquivado também não pode ser reutilizado por um projeto novo: herdar o
id seria herdar o histórico.

---

## 11. Como testar

```bash
cd apps/api

# unidade, repositório, segurança
.venv/Scripts/python -m pytest tests/test_project_registry.py -v

# PostgreSQL real (banco descartável)
docker exec <container> psql -U postgres -c "CREATE DATABASE veltrix_check;"
VELTRIX_TEST_POSTGRES_URL="postgresql://postgres:postgres@127.0.0.1:54322/veltrix_check" \
  .venv/Scripts/python -m pytest tests/test_project_registry_postgres.py -v
docker exec <container> psql -U postgres -c "DROP DATABASE veltrix_check;"

# no console
.venv/Scripts/python -m app.modules.risk_console
```

Sem `VELTRIX_TEST_POSTGRES_URL`/`PEDROCORE_TEST_POSTGRES_URL`, o arquivo de
PostgreSQL fica `skip` inteiro. Um PASS sem banco ali seria um PASS sobre nada.
