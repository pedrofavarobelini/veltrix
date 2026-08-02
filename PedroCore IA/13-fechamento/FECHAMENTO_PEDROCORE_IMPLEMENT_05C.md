# Fechamento — PEDROCORE-IMPLEMENT-05C — Artifact Reader final controlado

## Situação

O módulo `apps/api/app/modules/artifact_reader/` (criado no IMPLEMENT-04) já atendia às regras finais; esta subfrente **consolidou e provou** o comportamento com 4 testes adicionais, sem duplicar código.

## Regras confirmadas (todas testadas)

- Desabilitado por padrão (`PEDROCORE_ARTIFACT_READER_ENABLED=false`) — leitura bloqueada e path em payload segue rejeitado (`ARTIFACT_PATH_REJECTED`).
- Só lê dentro da allowlist (`PEDROCORE_ARTIFACT_ALLOWED_DIRS`); fora → `ARTIFACT_READER_PATH_NOT_ALLOWED`.
- `.env` bloqueado em qualquer lugar — incluindo estrutura aninhada `apps/api/.env` e variantes `.env.local`/`.env.production` (`ARTIFACT_READER_ENV_BLOCKED`, novo teste).
- Path traversal bloqueado; extensão fora de `.txt,.md,.log,.json,.csv` bloqueada; binário bloqueado; segredo identificável bloqueado (`ARTIFACT_READER_SECRET_BLOCKED`).
- Arquivo individual > `PEDROCORE_ARTIFACT_MAX_FILE_CHARS` bloqueado; **limite total por requisição** aplicado no serviço e no fluxo `/api/orchestrate` com múltiplos arquivos (`ARTIFACT_READER_TOTAL_LIMIT_EXCEEDED`, 2 novos testes).
- Nunca escreve, nunca deleta, nunca executa (teste de diretório idêntico antes/depois).
- FinGuard real nunca lido: caminho contendo "finguard" bloqueado no reader + reader indisponível para origem FinGuard na orquestração.
- Audit sem conteúdo lido (teste existente).

## Teste opt-in

A leitura real fora de `tmp_path` está coberta pelo fluxo opt-in geral (`PEDROCORE_RUN_REAL_INTEGRATION_TESTS`), que exige configuração humana de allowlist real — nunca apontando para o FinGuard.

## Resultado

`tests/test_artifact_reader.py`: 17 testes (13 anteriores + 4 novos), todos passando com `tmp_path`.

---

## Navegacao

- [[MOC_FECHAMENTOS]]
- [[MOC_PEDROCORE_IA]]
