# PedroCore IA

API pessoal de IA para testar qualidade de resposta, comportamento, contexto, histórico, feedback e integração com múltiplos provedores.

## Versão atual

**V4.0.0 — Interface melhorada do chat e experiência de uso**

A V4 mantém a base aprovada da V3 e melhora a interface React do chat:

- Sidebar de histórico local.
- Layout mais limpo e profissional.
- Bolhas modernas para usuário e IA.
- Botão copiar resposta.
- Feedback `Gostei` e `Não gostei` melhorado visualmente.
- Timestamp simples por mensagem.
- Estado de carregamento `PedroCore está pensando...`.
- Erro visual com opção de tentar novamente.
- Responsividade melhorada.

## Local correto

```txt
C:\Projetos\pedrocore-ia
```

O projeto deve ficar ao lado do FinGuard, nunca dentro dele:

```txt
C:\Projetos\FinGuard
C:\Projetos\pedrocore-ia
```

## Como rodar

Veja o arquivo:

```txt
COMANDOS_POWERSHELL.md
```

## Observação importante

O arquivo `.env` contém chaves reais e não deve ser versionado nem enviado para o GitHub.

Use `.env.example` como modelo seguro de configuração.

## Limitação da V4

A V4 melhora a interface, mas não cria banco, login, RAG, deploy ou GitHub. O histórico e os feedbacks continuam salvos apenas no navegador atual via `localStorage`.

## Git local e Obsidian

A V4 deve ser aplicada por cima da pasta local `C:\Projetos\pedrocore-ia`, preservando `.git` e `.env`.

Depois dos testes, salvar a versão no Git local:

```txt
commit: feat: melhorar interface do chat
tag: v4.0.0
```

A documentação foi atualizada em Markdown dentro de `docs`, compatível com Obsidian.

Documento principal da V4:

```txt
docs/11_V4_INTERFACE_CHAT.md
```
