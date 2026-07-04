# PedroCore IA — Status Atual

Atualizado em: 04/07/2026

## Status oficial

Em reformulação documental e estratégica. Este é o único documento de status oficial do projeto; prevalece sobre qualquer status antigo/duplicado ainda presente em `docs/`.

## Versão atual de produto

V5.1.9

## Frente atual

PEDROCORE-REPLAN-01A — Consolidação documental e visão oficial.

## Local oficial

```txt
C:\Projetos\pedrocore-ia
```

## Concluído

- Backend FastAPI com estrutura multi-provider (`BaseAIProvider`, `ProviderRegistry`, 6 providers: Mock, Gemini, OpenAI, Claude, DeepSeek, Grok).
- Endpoints `/`, `/health`, `POST /api/chat`, `GET /api/providers`.
- Fallback automático para `MockProvider` quando um provider real falha ou não está configurado.
- Frontend React/Vite/TypeScript com histórico local (`localStorage`), feedback gostei/não gostei, painel de configuração de providers e identidade visual aplicada (V5.1.9).
- Testes de backend cobrindo chat mock, fallback por provider desconhecido, validação de payload e listagem de providers.

## Em andamento

- Reformulação da documentação principal para refletir a visão de orquestrador central de IA (`PEDROCORE-REPLAN-01A`).
- Identificação e sinalização de documentos duplicados/desatualizados para consolidação futura (`PEDROCORE-REPLAN-01E`).

## Ainda não existe

- Task Router, Prompt Builder e Project Context (arquitetura-alvo, `PEDROCORE-REPLAN-01C`).
- Resposta estruturada por tipo de tarefa (hoje a resposta é texto livre em `answer: str`).
- Auditoria/log persistente de chamadas.
- Leitura de artefatos externos (relatórios de QA do FinGuard, documentação Obsidian) — planejada como somente leitura, ainda não implementada.
- QA Intelligence como caso de uso concreto.
- Persistência em banco de dados (histórico hoje só existe no navegador).
- Qualquer integração real com o FinGuard ou outro sistema externo.

## Proibido nesta fase

- Alterar código-fonte (`apps/api`, `apps/web`).
- Alterar frontend, componentes, estilos, layout ou design.
- Instalar dependências ou rodar servidor/testes.
- Chamar providers reais (Gemini, OpenAI, Claude, DeepSeek, Grok).
- Alterar `.env`.
- Ler ou escrever no repositório do FinGuard.
- Fazer commit ou remover documentação antiga nesta etapa.

## Riscos atuais

- **Documentação duplicada:** ainda existem pares de arquivos conflitantes em `docs/` (ex.: `docs/03_ROADMAP.md` vs `docs/03-versoes/ROADMAP.md`, `docs/09-status/STATUS_ATUAL.md` desatualizado) que não foram removidos nesta etapa, apenas sinalizados.
- **`GEMINI_API_KEY` configurada localmente:** o `.env` real do backend tem a chave do Gemini preenchida; qualquer execução do servidor com `provider=gemini` gera uma chamada real. Isso não foi alterado e deve ser tratado com cuidado em qualquer teste manual futuro.
- **Fallback Mock silencioso:** o fallback automático para `MockProvider` evita quebrar a interface, mas pode mascarar falhas reais de provider se o consumidor não checar explicitamente o campo `fallback_used` — especialmente relevante para futuros consumidores externos e para qualquer caso de uso de QA (ver Decisão Técnica 014).
- **Ausência de `task_type`/resposta estruturada:** a API atual não distingue tipos de tarefa nem devolve respostas estruturadas, o que limita o uso por sistemas externos além do chat conversacional atual.

## Próximos passos

- Executar `PEDROCORE-REPLAN-01B` — planejamento técnico e contratos de request/response para sistemas externos.
- Executar `PEDROCORE-REPLAN-01C` — arquitetura-alvo de Task Router, Prompt Builder e Project Context.
- Executar `PEDROCORE-REPLAN-01D` — planejamento de QA Intelligence.
- Consolidar/remover documentação duplicada em `PEDROCORE-REPLAN-01E`.
