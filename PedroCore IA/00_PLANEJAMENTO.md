# PedroCore IA — Planejamento Geral

## Objetivo

O PedroCore IA é uma API/assistente pessoal de inteligência artificial para testar respostas, qualidade, contexto, escrita, comportamento e formato das respostas de IA.

Não é objetivo treinar uma IA do zero. O objetivo é criar uma camada própria de uso e controle de IA, com possibilidade futura de conexão com outros projetos, como o FinGuard.

## Local oficial

```txt
C:\Projetos\pedrocore-ia
```

Estrutura correta:

```txt
C:\Projetos
  FinGuard
  pedrocore-ia
```

Estrutura errada:

```txt
C:\Projetos\FinGuard\pedrocore-ia
```

## Regras principais

1. PedroCore IA fica em `C:\Projetos\pedrocore-ia`.
2. FinGuard fica separado em `C:\Projetos\FinGuard`.
3. Nenhum comando do PedroCore IA deve ser executado dentro do FinGuard.
4. Todos os comandos devem ser enviados em blocos PowerShell organizados.
5. Toda alteração, erro, correção e decisão deve ser documentada.
6. A V1 deve ser simples e funcional.
7. Evoluir por versões controladas.

## Escopo da V1.0.1

- Backend Python com FastAPI.
- Endpoints `/`, `/health` e `/api/chat`.
- Provider mock.
- Frontend React com Vite e TypeScript.
- Interface simples de chat.
- Botão enviar.
- Botão copiar.
- Botão refazer.
- Botão gostei/não gostei.
- Painel de configurações simples.
- Prompt base editável.
- Feedback visual/toast nos botões.

---

## Navegacao

- [[MOC_HISTORICO_PEDROCORE]]
- [[MOC_PEDROCORE_IA]]
