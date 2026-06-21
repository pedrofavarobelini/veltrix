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
- CSS do toast agora já vem no ZIP.
- `ChatPage.tsx` já vem completo no ZIP.
- Documentação registra os erros anteriores.

### Status

Pronto para reinstalação limpa em `C:\Projetos\pedrocore-ia`.


## 0.1.2 ? Toast est?vel e configura??es melhoradas

Atualizado em: 20/06/2026 17:32:24

### Corrigido

- Toast agora cancela o timer anterior antes de exibir nova mensagem.
- Mensagens de configura??es abertas/fechadas foram removidas.
- Painel de configura??es ficou mais organizado.
- Adicionados bot?es Cancelar e Salvar e fechar.
- Adicionado bot?o X no painel de configura??es.

### Status

Aplicado.


## 0.1.3 ? Corre??o de acentua??o

Atualizado em: 20/06/2026 17:49:35

### Corrigido

- Textos da interface com acentua??o quebrada.
- Labels como Voc?, T?cnico, C?digo, Configura??es e N?o gostei.
- Prompt base padr?o com acentua??o correta.

### Status

Aplicado.

## Aprovação oficial — V1.0.4

Atualizado em: 20/06/2026 18:09:23

### Status

V1.0.4 aprovada.

### Validações concluídas

- Backend FastAPI funcionando.
- Endpoint /health funcionando.
- Endpoint /docs funcionando.
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

## Aprovação oficial — V2 Multi-provider com Gemini real

Atualizado em: 20/06/2026 23:18:07

### Status

V2 aprovada tecnicamente.

### Validações concluídas

- Backend FastAPI rodando.
- Endpoint /health funcionando.
- Endpoint /api/providers funcionando.
- Endpoint /api/chat funcionando com MockProvider.
- Endpoint /api/chat funcionando com GeminiProvider.
- Provider Gemini respondeu com fallback_used = False.
- Chave GEMINI_API_KEY validada.
- Frontend exibiu resposta do Gemini com acentuação correta.
- Arquitetura multi-provider mantida.

### Observação

O PowerShell exibiu acentuação quebrada em alguns testes, mas o frontend exibiu corretamente. O problema foi classificado como limitação de encoding/exibição do terminal, não como falha da API.

### Observação de melhoria futura

A resposta do Gemini apresentou pequeno erro de Markdown no início:

    *FastAPI**

O correto seria:

    **FastAPI**

Isso será tratado futuramente com melhoria no prompt base/formatação de resposta.

### Decisão

A V2 está aprovada como base multi-provider com Gemini real funcionando.

### Próxima versão

V3 — Histórico simples + feedback salvo.

## Aprovação final — V2 pela interface

Atualizado em: 20/06/2026 23:51:27

### Status

V2 aprovada pela interface web.

### Validações concluídas

- Frontend abriu em http://localhost:5173.
- Backend rodou em http://localhost:3333.
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
