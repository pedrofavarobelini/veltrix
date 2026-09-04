# Veltrix — Fluxo Completo

Atualizado em: 03/09/2026 · **ESTUDO ATUAL**

Quatro fluxos distintos passam pelo Veltrix. Confundi-los é o erro mais comum
ao estudar o sistema.

---

## Os quatro fluxos

| Fluxo | Entrada | Quem usa | Fallback |
|---|---|---|---|
| **1. Chat interativo** | `POST /api/chat` | a UI React do próprio Veltrix | **desligado** quando o usuário escolhe IA real |
| **2. Consumer integrado** | `POST /api/orchestrate` | FinGuard, Elyra, Structa | **ligado** (contrato original) |
| **3. Risk Engine** | `POST /api/risk/...`, CLI, Console | quem vai executar algo arriscado | não se aplica |
| **4. Learning / Evidence** | `/api/evidence`, `/api/operational-memory`, `/api/training-candidates` | o próprio sistema, governado | não se aplica |

---

## 1. Chat interativo — a UI do Veltrix

```text
ChatPage → ChatComposer → services/api → POST /api/chat
  → ChatRequest → ChatService → OrchestrationService
     → Caller Identity → Project Context → Policy
     → Provider Authorization → Provider Binding → Provider Catalog
     → Provider Registry → GeminiProvider → SDK
  → resposta ou falha → ChatResponse → MessageBubble
```

O que a UI envia quando o usuário escolheu explicitamente uma IA real:

```json
{
  "provider": "gemini",
  "model": "gemini-3.5-flash",
  "allow_real_provider": true,
  "allow_mock_fallback": false
}
```

## 2. Consumer integrado

```text
Front-end do consumidor → backend do consumidor
  → POST /api/orchestrate  (com credencial registrada)
  → mesmo pipeline central
  → resposta padronizada + warnings + audit
```

O consumidor **não** chama provider externo diretamente. E **não** envia
`allow_mock_fallback`: o default do contrato é `true`, então o fallback seguro
continua existindo para não deixá-lo sem resposta. Ele é responsável por
inspecionar `fallback_used`.

## 3. Risk Engine

```text
RiskRequest (contrato pedrocore-risk-request/v1)
  → Intent → Contexto resolvido → Prompt Quality → Ambiguidade → Escopo
  → Sinais → Findings → seis dimensões → Blast radius → Cenários
  → GATE:  ALLOW | REVIEW | BLOCK
  → Execution Contract assinado (HMAC)
        ⇣
   A EXECUÇÃO ACONTECE FORA DO VELTRIX (Agent / Test Harness)
        ⇣
  → Post-Execution QA: compara resultado × contrato
  → Execution Outcome V2 → Operational Memory → Historical Intelligence
```

O Veltrix **nunca** executa comando, migration, scanner ou teste. Ele recebe
resultados já produzidos e os confronta com o que havia autorizado.

## 4. Learning / Evidence

```text
Runtime Plane  ──(evidência validada, fail-closed)──►  Evidence Platform
   → Operational Memory / Retrieval
   → Dataset Foundation
   → Candidate Acquisition  (autorização explícita, nunca automática)
   → Training Foundation    → DATASET_NOT_READY
```

`automatic_collection = false` é invariante executável no Policy Engine. Dado
operacional **não** é candidato de treino.

---

## Os seis estados de um provider

Esta é a distinção que o Final Functional Gate tornou visível na interface:

| Estado | Pergunta que responde | Como se verifica |
|---|---|---|
| **conhecido** | o Veltrix sabe que existe? | está no Provider Catalog |
| **configurado** | há credencial no ambiente? | `GET /api/providers` → `configured` |
| **homologado** | foi aprovado para uso real? | `HOMOLOGATED_REAL` no catálogo |
| **autorizado** | *este* caller pode usá-lo agora? | matriz identidade + projeto + papel + ambiente |
| **executável** | poderia rodar? | implementado ∧ configurado ∧ homologado |
| **executado** | rodou **e respondeu**? | `provider` na resposta ∧ `fallback_used=false` |

Um provider **selecionado** na interface não é um provider **executado**. Essa
confusão era exatamente o bug.

## A matriz de autorização

```text
identity_strength + project_id + caller_role + environment + provider
   → ALLOWED | DENIED
```

Default: **negar**. Cada combinação precisa estar registrada explicitamente, e
o provider precisa estar implementado, configurado e homologado. Identidade
`ambiguous` (credencial compartilhada) não aparece em regra nenhuma e por isso
nunca alcança provider real, mesmo declarando `origin_system=finguard`.

## Semântica final do fallback

Esta é a correção central do Final Functional Gate.

**Antes:** qualquer falha do provider real virava resposta do Mock, apresentada
como resposta normal — `provider="mock"`, `fallback_used=true`, `status="ok"` —
enquanto a interface continuava exibindo "Gemini".

**Depois**, no chat interativo com IA real escolhida explicitamente:

| Situação | provider | model | fallback | O que a UI mostra |
|---|---|---|---|---|
| Gemini respondeu | `gemini` | `gemini-3.5-flash` | `false` | a resposta do Gemini |
| Gemini falhou | `none` | `none` | `false` | "Gemini não concluiu a solicitação." |
| Safe mode bloqueou | `mock` | `mock-v1` | `true` | fallback declarado + aviso |
| Provider interno (dev) | `mock` | `mock-v1` | `false` | resposta do Mock, rotulada `DEV` |

Para consumers integrados **nada mudou**: `allow_mock_fallback` continua `true`
por padrão. A mudança é de boundary, não global.

E as mensagens de erro passaram a depender do contexto: o disclaimer financeiro
pertence ao FinGuard e saiu do chat geral.

## Onde o release gate entra

Só `local_qa`, com evidência textual limpa, risco baixo, sem fallback e sem
safe-mode block, pode liberar `release_gate_review`. Provider real e Mock nunca
aprovam release gate sozinhos.

## Links relacionados

- [[../MOC_ESTUDO_PEDROCORE]]
- [[PEDROCORE_MAPA_MENTAL]]
- [[PEDROCORE_GLOSSARIO]]
- [[VELTRIX_RISK_ENGINE_ESTUDO]]
- [[../10-contratos/CONTRATO_ORQUESTRACAO]]
- [[../19-encerramento-final/VELTRIX_FINAL_FUNCTIONAL_GATE]]
