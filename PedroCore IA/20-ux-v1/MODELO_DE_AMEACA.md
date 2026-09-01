# Modelo de ameaça — cenários A, B, C e D

Mapa da frente: [[MOC_UX_V1]].

O PedroCore é seguro **para os usos que ele realmente tem hoje**, e não é
seguro para um uso que ele nunca teve. Este documento separa os quatro cenários
para que essa diferença não vire nem alarme falso nem falsa confiança.

## Resumo

| Cenário | Descrição | Veredito |
| --- | --- | --- |
| **A** | Uso local, só na máquina do proprietário | **SEGURO** |
| **B** | Ecossistema local (FinGuard, Structa e outros consumindo o PedroCore) | **SEGURO** |
| **C** | Código público no GitHub, sem API exposta | **SEGURO** |
| **D** | API exposta à internet | **NÃO SEGURO** — requisitos de deploy pendentes |

---

## Cenário A — uso local

**SEGURO.**

- Credenciais só no backend, lidas de `.env` por `core/config.py`. `.env` não é
  rastreado e nunca foi (verificado em todo o histórico Git).
- O frontend nunca vê chave: o `localStorage` guarda apenas preferências e o
  **ID** do provider autorizado.
- Safe mode: `allow_real_provider=false` por padrão. Provider real sem
  autorização explícita vira `PROVIDER_REAL_BLOCKED` + fallback Mock.
- CORS restrito a `localhost:5173` / `127.0.0.1:5173` por default.
- Observabilidade é **default-off**, volátil e exige **loopback**.
- Sem XSS: nenhum `dangerouslySetInnerHTML`, `innerHTML` ou `eval` em
  `apps/web/src`.
- Áudio do microfone não é gravado, guardado nem enviado ao PedroCore.
- Anexos são validados por allowlist, limitados e nunca executados; o nome de
  arquivo é metadado e jamais vira caminho.

## Cenário B — ecossistema local

**SEGURO.**

A defesa aqui não é rede, é **identidade**:

- `PEDROCORE_CALLER_REGISTRY` é a única forma de estabelecer
  `identity_strength=registered`, e portanto a única forma de um consumidor
  alcançar provider real.
- Com registry configurado, o comportamento é **fail-closed**: sem credencial,
  com credencial não registrada ou com JSON inválido, a requisição é rejeitada.
- A **origem declarada no payload é só alegação**: `validate_origin_claim`
  compara com a identidade da credencial; divergiu, bloqueia
  (`CALLER_ORIGIN_MISMATCH`).
- Credencial **global compartilhada** não identifica projeto: produz
  `identity_strength=ambiguous`, que a matriz de autorização **sempre nega**
  para provider real.
- A matriz é explícita por `identity_strength × project_id × caller_role ×
  environment × provider`. Combinação não registrada é negada por default.
- Negação **nunca vira chamada real**: vira fallback Mock seguro.
- Isolamento comprovado por teste: FinGuard e Structa têm escopos distintos;
  Structa só alcança `qa_report_analysis`, só Gemini, só ambiente não produtivo,
  só com papel `technical_tool`.

## Cenário C — código público no GitHub

**SEGURO.**

- Nenhum `.env` rastreado no HEAD nem em **todo o histórico**.
- Nenhum arquivo `.pem`, `.key`, `.p12`, `.pfx`, `.keystore`, `.db`, `.dump`
  ou `.bak` jamais adicionado ao Git.
- Varredura por padrões de credencial real (Google `AIza…`, OpenAI `sk-…`,
  Anthropic `sk-ant-…`, xAI `xai-…`, token GitHub, AWS `AKIA…`, bloco de chave
  privada, Bearer literal): **nenhum segredo real**.
  - Único casamento: `SECRET_LOOKING_KEY` em
    `tests/test_output_budget_observability.py` — literal preenchido com
    `DUMMY`, fixture sintética deliberada que testa se o sanitizador redige
    strings com formato de chave. **Falso positivo.**
- `.env.example` contém apenas placeholders vazios e documentação; nenhum valor
  real. O próprio arquivo instrui a nunca versionar `api_key`.
- `.gitignore` cobre `.env`, `.env.*` (exceto `.env.example`), `.venv/`,
  `node_modules/`, `dist/`, caches, logs, `*.bak*` e `*.tsbuildinfo`.
- Publicar o código **não** publica a API. São decisões separadas.

## Cenário D — API pública na internet

**NÃO SEGURO no estado atual.** Isto é limitação conhecida e aceita, não defeito
de implementação — o PedroCore nunca foi construído para esse cenário.

### Lacunas

| Lacuna | Situação |
| --- | --- |
| Autenticação no `/api/chat` | **ausente** — o endpoint é aberto por design, para compatibilidade com o próprio frontend |
| Autenticação no `/api/orchestrate` e `/api/reports/*` | **opcional** — só exigida quando `PEDROCORE_INTERNAL_API_KEY` está configurada |
| Rate limiting | **inexistente** |
| Controle de custo por consumidor | **inexistente** |
| TLS | responsabilidade do proxy; não há terminação própria |
| Limite de tamanho de payload | apenas os limites de artefato; não há teto global de corpo |
| CORS | restrito por default, mas **CORS não é autenticação** e não protege chamada fora do navegador |
| Observabilidade | protegida por loopback — o que já a torna imprópria para exposição, e é o comportamento correto |

### O que já protege, mesmo em D

Vale registrar que o pior caso — custo externo descontrolado — **já tem freio**:
a regra `local_trusted` da matriz de autorização vale apenas para
`NON_PRODUCTION_ENVIRONMENTS`. Com `APP_ENV=production`, um caller não
autenticado **não** obtém provider real; cai em Mock. Isso não substitui
autenticação, mas evita que a exposição vire conta de API.

### Requisitos obrigatórios antes de expor

1. autenticação **obrigatória** no `/api/chat`, não opcional;
2. rate limiting por credencial e por IP;
3. teto de payload no servidor ou no proxy;
4. TLS terminado por proxy reverso;
5. `APP_ENV=production` explícito, para que a matriz feche o caminho não
   autenticado;
6. CORS restrito ao domínio real do frontend;
7. orçamento/quota por consumidor;
8. observabilidade persistente e protegida, se for necessária em produção.

Nada disso bloqueia os cenários A, B e C.

## Relacionados

- [[MOC_SEGURANCA]] — safe mode, policy e limites.
- [[16-qa-safety-hardening/PROVIDER_REAL_SAFETY]] — provider real default-off.
- [[17-multi-provider-safe-evolution/ETAPA_2_IDENTIDADE_AUTORIZACAO]] — identidade e matriz.
- [[17-multi-provider-safe-evolution/FIX_CREDENCIAL_COMPARTILHADA]] — credencial ambígua.
- [[20-ux-v1/PEDROCORE_V1_FINAL_CLOSURE_01]] — gates finais.
