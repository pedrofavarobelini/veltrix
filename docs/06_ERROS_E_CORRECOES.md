# PedroCore IA — Erros e Correções

## Erro 001 — ZIP inicial com risco de pasta raiz errada

Status: corrigido.

## Erro 002 — Caminho do projeto mal interpretado

Caminho oficial definido:

```txt
C:\Projetos\pedrocore-ia
```

Status: corrigido.

## Erro 003 — uv não reconhecido

Correção: uv instalado via instalador oficial.

Status: corrigido.

## Erro 004 — pip não reconhecido

Diagnóstico: pip não estava acessível diretamente no PowerShell.

Status: contornado com uv.

## Erro 005 — Documentação incompleta

Correção: documentação em Markdown/Obsidian criada.

Status: corrigido.

## Erro 006 — GET / retornava 404

Correção na V1.0.1: adicionada rota raiz `/`.

Status: corrigido.

## Erro 007 — Botões sem feedback visual

Correção na V1.0.1: adicionado toast visual no frontend.

Status: corrigido.

## Erro 008 — Script de patch colado parcialmente no PowerShell

Diagnóstico: o bloco deveria criar um `.ps1`, mas foi executado parcialmente. Variáveis ficaram nulas e o PowerShell tentou escrever em caminhos como `C:\05_TESTES.md`.

Correção: gerar novo ZIP limpo V1.0.1 revisado.

Status: corrigido pelo ZIP revisado.


---

## Corre??o 009 ? Toast com tempo inconsistente e configura??es simples demais

Atualizado em: 20/06/2026 17:32:24

### Situa??o

Ap?s a V1.0.1, as mensagens de feedback come?aram a aparecer, mas foi observado que o tempo do toast ficava inconsistente ao clicar rapidamente em bot?es diferentes.

Tamb?m foi identificado que o painel de configura??es estava simples demais e exibia mensagens desnecess?rias ao abrir/fechar.

### Diagn?stico

O toast usava setTimeout sem limpar o timer anterior. Assim, um timer antigo podia apagar uma mensagem nova antes do tempo esperado.

### Corre??o aplicada

- Adicionado useRef para controlar o timer do toast.
- O timer anterior ? cancelado antes de abrir uma nova mensagem.
- Removidas mensagens ao abrir/fechar configura??es.
- Painel de configura??es recebeu melhorias visuais.
- Bot?o simples de fechar foi substitu?do por bot?o X, Cancelar e Salvar e fechar.

### Arquivos alterados

- apps/web/src/pages/ChatPage.tsx
- apps/web/src/styles/global.css

### Backups criados

- ChatPage.tsx.bak-v1.0.2
- global.css.bak-v1.0.2

### Status

Corrigido.


---

## Corre??o 011 ? Acentua??o quebrada na interface

Atualizado em: 20/06/2026 17:49:35

### Situa??o

A interface passou a exibir caracteres como ponto de interroga??o no lugar de acentos.

Exemplos:

- Configura??es
- T?cnico
- Voc?
- N?o gostei

### Diagn?stico

O arquivo React foi salvo anteriormente com problema de encoding durante aplica??o de patch via PowerShell.

### Corre??o aplicada

O arquivo ChatPage.tsx foi regravado em UTF-8 usando escapes Unicode para preservar acentua??o.

### Arquivo alterado

- apps/web/src/pages/ChatPage.tsx

### Backup criado

- ChatPage.tsx.bak-v1.0.3

### Status

Corrigido.

---

## Correção 012 — Texto Unicode aparecendo na interface

Atualizado em: 20/06/2026 18:04:59

### Situação

A interface exibiu textos quebrados como:

    Configura\u00e7\u00f5es
    T\u00e9cnico
    N\u00e3o gostei

### Diagnóstico

A tentativa anterior usou escapes Unicode de forma incorreta, fazendo com que eles aparecessem visualmente na tela.

### Correção aplicada

O arquivo ChatPage.tsx foi regravado em UTF-8 com textos diretos e centralizados no objeto UI.

### Arquivo alterado

    apps\web\src\pages\ChatPage.tsx

### Backup criado

    ChatPage.tsx.bak-v1.0.4

### Status

Corrigido.
