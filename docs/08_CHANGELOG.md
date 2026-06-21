# PedroCore IA — Changelog

## 0.1.1 — ZIP revisado

### Adicionado

- Rota `GET /`.
- Feedback visual nos botões.
- Toast de confirmação.
- Documentação revisada.
- Teste automático da rota raiz.

### Corrigido

- Fluxo quebrado do patch anterior.
- CSS do toast incluído diretamente no ZIP.
- `ChatPage.tsx` incluído completo no ZIP.
- Documentação registra os erros anteriores.

### Status

Pronto para reinstalação limpa em `C:\Projetos\pedrocore-ia`.

---

## 0.1.2 — Toast estável e configurações melhoradas

Atualizado em: 20/06/2026 17:32:24

### Corrigido

- Toast agora cancela o timer anterior antes de exibir nova mensagem.
- Mensagens de configurações abertas/fechadas foram removidas.
- Painel de configurações ficou mais organizado.
- Adicionados botões Cancelar e Salvar e fechar.
- Adicionado botão X no painel de configurações.

### Status

Aplicado.

---

## 0.1.3 — Correção de acentuação

Atualizado em: 20/06/2026 17:49:35

### Corrigido

- Textos da interface com acentuação quebrada.
- Labels como Você, Técnico, Código, Configurações e Não gostei.
- Prompt base padrão com acentuação correta.

### Status

Aplicado.

---

## Aprovação oficial — V1.0.4

Atualizado em: 20/06/2026 18:09:23

### Status

V1.0.4 aprovada.

### Validações concluídas

- Backend FastAPI funcionando.
- Endpoint `/health` funcionando.
- Endpoint `/docs` funcionando.
- Frontend React funcionando.
- Chat enviando mensagem.
- MockProvider respondendo.
- Botão Copiar funcionando.
- Botão Gostei funcionando.
- Botão Não gostei funcionando.
- Botão Refazer funcionando.
- Painel Config funcionando.
- Toast com tempo estável.
- Configurações sem toast desnecessário.
- Acentuação da interface corrigida.
- Textos quebrados removidos.

### Decisão

A V1.0.4 está estável o suficiente para servir como base da V2.

### Próxima versão

V2 — Integração real com Gemini.

---

## Aprovação oficial — V2 Multi-provider com Gemini real

Atualizado em: 20/06/2026 23:18:07

### Status

V2 aprovada tecnicamente.

### Validações concluídas

- Backend FastAPI rodando.
- Endpoint `/health` funcionando.
- Endpoint `/api/providers` funcionando.
- Endpoint `/api/chat` funcionando com MockProvider.
- Endpoint `/api/chat` funcionando com GeminiProvider.
- Provider Gemini respondeu com `fallback_used = False`.
- Chave `GEMINI_API_KEY` validada localmente.
- Frontend exibiu resposta do Gemini com acentuação correta.
- Arquitetura multi-provider mantida.

### Observação

O PowerShell exibiu acentuação quebrada em alguns testes, mas o frontend exibiu corretamente. O problema foi classificado como limitação de encoding/exibição do terminal, não como falha da API.

### Observação de melhoria futura

A resposta do Gemini apresentou pequeno erro de Markdown no início:

```txt
*FastAPI**
```

O correto seria:

```txt
**FastAPI**
```

Isso será tratado futuramente com melhoria no prompt base/formatação de resposta.

### Decisão

A V2 está aprovada como base multi-provider com Gemini real funcionando.

### Próxima versão

V3 — Histórico simples + feedback salvo.

---

## Aprovação final — V2 pela interface

Atualizado em: 20/06/2026 23:51:27

### Status

V2 aprovada pela interface web.

### Validações concluídas

- Frontend abriu em `http://localhost:5173`.
- Backend rodou em `http://localhost:3333`.
- MockProvider respondeu pela interface.
- GeminiProvider respondeu pela interface.
- Gemini retornou resposta real.
- Acentuação validada no navegador.
- Botões principais testados.
- Painel de configurações testado.
- Problema de npm registry corrigido.

### Decisão

A V2 está aprovada como base multi-provider com Gemini real funcionando.

### Próxima versão

V3 — Histórico simples + feedback salvo.

---

## V3.0.0 — Histórico local e feedback simples

Atualizado em: 21/06/2026

### Adicionado

- Histórico local de mensagens no frontend.
- Persistência do histórico via `localStorage`.
- Feedback `Gostei` e `Não gostei` por resposta da IA.
- Persistência do feedback após recarregar a página.
- Identificador único por mensagem.
- Contador de mensagens salvas no histórico local.
- Botão para limpar histórico local.
- Limite técnico de 100 mensagens de conversa.
- Documento `docs/10_V3_HISTORICO_E_FEEDBACK.md`.

### Mantido

- Backend FastAPI sem alteração funcional.
- Estrutura multi-provider da V2.
- GeminiProvider.
- MockProvider.
- Fallback para MockProvider.

### Revisado na entrega final

- Entrega normalizada em ZIP único.
- `COMANDOS_POWERSHELL.md` atualizado para V3.0.0.
- Removidos arquivos locais desnecessários da entrega.
- Documentação revisada para corrigir acentuação quebrada.
- `.env`, `.git`, `.venv`, `node_modules`, `dist` e caches removidos do ZIP.

### Status

Implementado para testes. Aguardando aprovação final pela interface.
