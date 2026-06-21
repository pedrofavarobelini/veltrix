# V3 — Git e Versionamento Local

Atualizado em: 21/06/2026

## Objetivo

Registrar corretamente a V3.0.0 do PedroCore IA no Git local depois da aplicação do ZIP, dos testes e da conferência da documentação no Obsidian.

## Situação esperada antes da V3

- Projeto local em `C:\Projetos\pedrocore-ia`.
- Git local já iniciado.
- Tag `v2.0.0` existente.
- GitHub remoto ainda não usado.
- `.env` real existente localmente, mas não versionado.

## Regra crítica

O ZIP da V3 não deve substituir a pasta inteira apagando `.git`.

A aplicação correta é copiar os arquivos da V3 por cima do projeto existente.

## Conferir versão anterior

```powershell
cd C:\Projetos\pedrocore-ia

git log --oneline --decorate -5

git tag
```

A tag `v2.0.0` deve aparecer.

## Conferir arquivos sensíveis

```powershell
cd C:\Projetos\pedrocore-ia

git ls-files | Select-String "\.env"
```

Resultado permitido:

```txt
apps/api/.env.example
```

Resultado proibido:

```txt
apps/api/.env
```

## Conferir mudanças da V3

```powershell
cd C:\Projetos\pedrocore-ia

git status --short

git diff --stat
```

## Adicionar arquivos da V3

```powershell
cd C:\Projetos\pedrocore-ia

git add README.md VERSION.md COMANDOS_POWERSHELL.md .gitignore apps/web/src/pages/ChatPage.tsx apps/web/src/styles/global.css apps/web/src/types/chat.ts apps/web/src/utils/chatStorage.ts docs/04-comandos/V3_COMANDOS.md docs/04-comandos/V3_GIT_VERSIONAMENTO.md docs/06_ERROS_E_CORRECOES.md docs/08_CHANGELOG.md docs/09_STATUS_ATUAL.md docs/10_V3_HISTORICO_E_FEEDBACK.md
```

## Conferir staging

```powershell
git status --short
```

## Criar commit da V3

```powershell
git commit -m "feat: adicionar historico local e feedback das respostas"
```

## Criar tag da V3

```powershell
git tag v3.0.0
```

## Conferir resultado

```powershell
git log --oneline --decorate -5

git tag

git status
```

Resultado esperado:

- Commit da V3 criado.
- Tag `v3.0.0` apontando para o commit da V3.
- Tag `v2.0.0` preservada.
- Working tree clean.

## Ainda não fazer

- Não subir para GitHub ainda.
- Não criar repositório remoto ainda.
- Não expor `.env`.
- Não mexer no FinGuard.

## Próxima etapa depois da aprovação

Após V3 aprovada e versionada localmente, iniciar V4:

```txt
V4 — Melhorias de interface do chat e experiência de uso.
```
