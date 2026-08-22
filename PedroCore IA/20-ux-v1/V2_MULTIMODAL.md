# V2 — MULTIMODAL

Mapa da frente: [[MOC_UX_V1]].

Status: **adiado formalmente para a V2**, por decisão técnica registrada, não
por falta de tempo.

A V1 **não deve ser considerada incompleta** por não ter multimodal: a
implementação correta exige arquitetura nova, e forçá-la nesta frente violaria o
princípio do menor diff e quebraria contratos congelados.

## Estado atual — o que já existe

O substrato de *reconhecimento* existe e é honesto sobre a própria limitação:

- `artifacts/service.py` define
  `VISUAL_ARTIFACT_TYPES = {screenshot, image, playwright_trace, pdf, binary}`.
  Artefato visual é **aceito, registrado e avisado**, nunca analisado:
  `"Artefato visual recebido, mas análise visual ainda não está implementada."`
- `visual_qa/service.py` devolve `VisualQAAnalysis` com `supported=False`,
  `mode="stub"`, `can_advance=False`, `requires_human_review=True` e uma lista
  de verificações manuais sugeridas.
- Release gate **nunca avança** só com evidência visual não analisada.
- Três flags existem e são **default OFF**:
  `PEDROCORE_MULTIMODAL_PROVIDER_ENABLED`, `PEDROCORE_VISUAL_QA_ENABLED`,
  `PEDROCORE_OCR_ENABLED`.
- Mesmo com **todas** as flags ligadas, `evaluate_real_visual_guard` não
  executa envio: registra
  `"contrato preparado; execução exige frente futura com confirmação humana"`.

Ou seja: nenhuma imagem é enviada a provider externo hoje, por construção.

## Lacunas reais — por que não é aditivo

### 1. A assinatura do adapter só carrega texto

```python
# providers/base.py
async def generate_response(
    self, message: str, mode: str, model: str, system_prompt: str | None = None
)
```

Não há parâmetro para partes não textuais. Suportar imagem exige **mudar o
contrato de `BaseAIProvider`** e, com ele, os sete adapters
(`mock`, `gemini`, `openai`, `claude`, `deepseek`, `grok`, `local_model`).
Isso é mudança estrutural, não adição.

### 2. O adapter Gemini é texto puro

`gemini_provider.py` não tem qualquer tratamento de `inline_data`, `parts`,
`mime_type` ou base64. Multimodal exigiria reescrever a montagem da requisição,
o orçamento de saída e a contagem de tokens — que hoje assume entrada textual.

### 3. O Prompt Builder monta um bloco de texto

`prompt_builder` recebe `artifacts_text_block: str`. Imagem não tem
representação nesse contrato sem o hack explicitamente proibido de enfiar
base64 gigante no prompt.

### 4. Transporte e limites são de caractere

Os limites do pipeline são `MAX_ARTIFACT_CONTENT_CHARS` e
`MAX_TOTAL_ARTIFACT_CHARS` — contam **caracteres**. Binário precisa de limites
por bytes, validação de tipo real por assinatura de arquivo (magic bytes, não
extensão) e um caminho de transporte que não seja JSON de texto.

## O que a V2 precisa construir

### Arquitetura

- parâmetro de partes multimodais no contrato de `BaseAIProvider`, com default
  que preserve retrocompatibilidade de todos os adapters atuais;
- capability por adapter (`supports_multimodal`) no `provider_catalog`, para
  que o roteamento nunca escolha um provider incapaz;
- caminho de transporte binário — endpoint próprio ou parte multipart — em vez
  de string no JSON atual.

### Contratos

- novo tipo de artefato com `mime_type` e `bytes`, distinto de
  `ArtifactInput.content: str`;
- resposta com `visual_qa_analysis` de fato preenchido, substituindo o stub;
- códigos de warning novos, aditivos, sem quebrar consumidor existente.

### Segurança

- validação por **magic bytes**, não por extensão nem por MIME do cliente;
- limites por bytes e por dimensão de imagem;
- decisão explícita sobre custo: imagem consome muito mais token que texto, e
  o orçamento de saída atual não modela isso;
- política de autorização própria — enviar a imagem de um usuário a um provider
  externo é uma decisão de privacidade diferente de enviar texto que ele
  digitou;
- garantia de que artefato visual continua **sem aprovar release gate** sozinho.

### Testes

- adapters com fake multimodal, sem rede;
- guard de capability: provider sem suporte nunca recebe imagem;
- limites de bytes e recusa por magic byte incoerente;
- regressão de que payload somente-texto continua idêntico ao da V1.

## Decisão

Multimodal fica na V2. A V1 entrega **anexos textuais reais** — ver
[[20-ux-v1/VOZ_E_ANEXOS]] — que cobrem `.txt`, `.md`, `.markdown`, `.csv`,
`.json` e `.log` pelo contrato já existente, sem tocar no backend.

## Relacionados

- [[20-ux-v1/VOZ_E_ANEXOS]] — o que a V1 entregou no lugar.
- [[12-qa-intelligence/QA_INTELLIGENCE_OVERVIEW]] — QA visual no plano original.
- [[MOC_SEGURANCA]] — guards de OCR/multimodal/Playwright.
- [[03-versoes/ROADMAP]] — posição da V2 no roadmap.
