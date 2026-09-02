# Etapa 4 — Política determinística em shadow mode

Frente: `PEDROCORE-MULTI-PROVIDER-SAFE-EVOLUTION`.

Status: **concluída e reconciliada com a correção `8c97004`, com efeito nulo
comprovado sobre a execução real**.

## Objetivo

Calcular, de forma determinística, qual provider/modelo uma política
multi-provider futura escolheria — **sem alterar a execução real, sem chamar
provider algum e sem consultar uma segunda IA**.

```
requisição recebida
→ identidade e autorização (Etapa 2)
→ binding provider/modelo (Etapa 3)
→ calcula decisão shadow
→ registra decisão shadow
→ continua no roteamento real atual (Gemini-only)
→ executa no máximo uma IA
```

## Onde

- `apps/api/app/modules/shadow_routing/` — política, candidatos e decisão.
- `apps/api/app/modules/orchestration/service.py` — cálculo (não lido pela
  execução) e comparação por identificadores após a execução.
- `apps/api/tests/test_shadow_routing.py` — testes da etapa.

## Política

Sem score dinâmico, custo, latência, health, estatística, aprendizado, A/B,
ensemble, votação, execução paralela ou comparação de respostas. Apenas:

```
filtros eliminatórios → prioridade estática por projeto/task → desempate
```

### Filtros eliminatórios

Avaliados nesta ordem, produzindo o motivo mais informativo:

`not_registered` → `not_implemented` → `not_configured` → `not_homologated` →
`ambiguous_identity` → `not_authorized` → `task_incompatible` →
`project_policy_blocked` → `model_incompatible` →
`model_not_homologated` → `model_not_authorized` → `safe_mode_blocked`.

Ter chave configurada **não** torna um candidato elegível: com chave, Claude e
OpenAI são eliminados por `not_homologated`; sem chave, por `not_configured`.
Identidade `ambiguous` não produz nenhum candidato real elegível.

Depois da correção `8c97004`, os filtros de modelo consultam somente entradas
explícitas de `_MODEL_CATALOG`:

- modelo configurado desconhecido é eliminado como `model_incompatible`;
- modelo conhecido, mas não homologado, é eliminado como
  `model_not_homologated`;
- modelo conhecido, homologado, mas não autorizado, é eliminado como
  `model_not_authorized`;
- incompatibilidade com a task também elimina o candidato antes de qualquer
  execução.

Configuração runtime não cria candidato shadow e não promove homologação. O
binding é consultado apenas como validação da combinação; sua resposta nunca
entra no caminho de execução real.

### Prioridade estática e desempate

Declarada em código, em tuplas ordenadas (nunca dict/set em iteração):

| Projeto | Task | Preferência |
| --- | --- | --- |
| `finguard`, `finguard-local` | qualquer | `gemini` → `claude` → `openai` |
| `pedrocore` | qualquer | `gemini` → `claude` → `openai` |
| qualquer outro | qualquer | `gemini` → `claude` → `openai` |

O desempate é a própria ordem estática: vence o **primeiro sobrevivente**.
Claude e OpenAI aparecem como conhecidos e potencialmente priorizados, mas são
sempre eliminados pelo motivo correto — nunca autorizados artificialmente para
produzir uma decisão diferente.

## Ativação

Flag `PEDROCORE_SHADOW_ROUTING_ENABLED`, **default desligado**. O controle
pertence ao Veltrix: nada no payload liga ou desliga o shadow, e o FinGuard
não pode enviar `shadow=true`.

## Efeito nulo

Com o shadow ligado ou desligado, para a mesma entrada e os mesmos stubs, são
idênticos: provider executado, modelo executado, número de chamadas, resposta
pública, status, fallback, release gate e warnings. Somente auditoria e
observabilidade internas ganham informação.

`would_differ_from_actual` é calculado **apenas** comparando identificadores,
depois da execução real. O candidato planejado nunca é executado.

As sondas específicas comprovam que modelo configurado arbitrário não se torna
conhecido/homologado e que modelo explicitamente conhecido, porém não
homologado, é eliminado. O fechamento após `8c97004` registrou
`515 passed, 7 skipped`, eval harness `14/14` e zero chamadas reais.

## Observabilidade e auditoria

A observabilidade distingue `provider_shadow_planned` / `model_shadow_planned`
de `provider_effective` / `model_effective`, e lista todos os candidatos com
seus motivos de eliminação. A auditoria guarda um resumo sanitizado
(`shadow_enabled`, `shadow_selected_provider`, `shadow_selected_model`,
`shadow_would_differ`, `shadow_policy_version`). Nenhum segredo entra na
decisão.

O contrato público de `POST /api/orchestrate` não ganhou campo de shadow, e a
projeção do frontend segue limitada a `answer`, `suggestions`, `disclaimer`.

## O que esta etapa NÃO faz

- não altera `AUTO_REAL_PROVIDER_CANDIDATES` (segue `("gemini",)`);
- não autoriza Claude/OpenAI, não executa candidato planejado;
- não implementa multi-provider real, health, circuit breaker ou fallback
  entre providers reais;
- não inicia a Etapa 5.

---

## Navegacao

- [[MOC_MULTI_PROVIDER_SAFE_EVOLUTION]]
- [[MOC_FECHAMENTOS]]
