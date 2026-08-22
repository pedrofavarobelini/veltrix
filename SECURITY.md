# Política de Segurança — PedroCore IA

## Reportar uma vulnerabilidade

Se você encontrar uma vulnerabilidade, **não abra uma issue pública**.

Use o canal privado do GitHub — *Security* → *Report a vulnerability* — ou entre
em contato diretamente com o mantenedor do repositório.

Inclua, no que for possível:

- o que é afetado (endpoint, módulo, arquivo);
- como reproduzir;
- o impacto que você acredita existir;
- versão/commit em que observou.

Você receberá confirmação de recebimento. Correções e divulgação são
coordenadas com quem reportou.

Este é um projeto pessoal, mantido por uma pessoa. Não há SLA de resposta e não
há programa de recompensa.

## Modelo de segredos

**Chaves de API vivem exclusivamente no backend.**

- São lidas de `apps/api/.env` por `app/core/config.py`.
- `.env` **nunca** deve ser versionado. Só `apps/api/.env.example` vai para o
  Git, contendo apenas placeholders vazios e documentação.
- O `.gitignore` cobre `.env` e `.env.*`, com exceção explícita de
  `.env.example`.
- O frontend **nunca** recebe, guarda ou transmite chave alguma. O
  `localStorage` do navegador guarda preferências de interface e o
  *identificador* do provider que o usuário autorizou — isso é consentimento,
  não credencial.
- `PEDROCORE_CALLER_REGISTRY` contém segredos de consumidores e deve ser
  fornecido por ambiente/runtime. O exemplo versionado traz apenas
  `"<somente por ambiente/runtime; NUNCA versionar>"` no lugar do valor.

Se uma chave for exposta por engano, considere-a comprometida: revogue e gere
outra no painel do provider. Remover o commit não desfaz a exposição.

## Postura padrão: uso local

A configuração distribuída é para rodar **na máquina do desenvolvedor**.

- Provider padrão é `mock`: sem rede, sem chave, sem custo.
- `allow_real_provider=false` por padrão — nenhum provider real é chamado sem
  autorização explícita na requisição.
- CORS restrito a `localhost:5173` / `127.0.0.1:5173`.
- Observabilidade técnica é default-off, volátil e só responde a **loopback**.
- Recursos de maior risco — provider generativo local, OCR, multimodal,
  Playwright, circuit breaker, fallback real e persistência de memória — são
  todos **default OFF** e exigem opt-in explícito.
- Com registro de callers configurado, o comportamento é **fail-closed**:
  requisição sem credencial ou com credencial desconhecida é rejeitada.

## Publicar o código não é publicar a API

Este repositório ser público significa que o **código-fonte** é público. Não
significa que existe um serviço exposto, nem que o projeto esteja pronto para
ser exposto.

### Limitações conhecidas de deploy

Antes de colocar esta API na internet, o seguinte é **obrigatório** e ainda não
existe:

1. **Autenticação no `POST /api/chat`** — hoje o endpoint é aberto, por
   compatibilidade e para servir o frontend local. A autenticação existente
   (`PEDROCORE_INTERNAL_API_KEY`) cobre `/api/orchestrate` e `/api/reports/*`, e
   mesmo assim só é exigida quando configurada.
2. **Rate limiting** por credencial e por IP — inexistente.
3. **Teto global de tamanho de payload** — só há limites por artefato.
4. **TLS** — não há terminação própria; depende de proxy reverso.
5. **`APP_ENV=production` explícito** — em produção a matriz de autorização
   fecha o caminho não autenticado ao provider real.
6. **CORS restrito** ao domínio real do frontend. CORS **não é autenticação**:
   ele só restringe navegadores, não clientes HTTP diretos.
7. **Quota/orçamento por consumidor**, para que um chamador não gere custo
   ilimitado de provider externo.

Uma nota atenuante, que não substitui os itens acima: com `APP_ENV=production`,
um chamador não autenticado **não** obtém provider real — a regra de identidade
local só vale em ambientes não produtivos. Isso limita o custo de uma exposição
acidental, mas não a torna aceitável.

## Escopo

**Dentro do escopo:** vazamento de credencial, contorno da matriz de
autorização de providers, contorno do safe mode, path traversal via artefatos,
XSS no frontend, exposição indevida de dados na observabilidade.

**Fora do escopo:** ausência de autenticação no `/api/chat`, ausência de rate
limiting e ausência de TLS — são limitações **conhecidas e documentadas** do
modelo de uso local, listadas acima. Relatá-las é bem-vindo como discussão, mas
não são vulnerabilidades não divulgadas.

## Referências

- `PedroCore IA/20-ux-v1/MODELO_DE_AMEACA.md` — cenários A/B/C/D em detalhe.
- `PedroCore IA/MOC_SEGURANCA.md` — mapa dos controles de segurança.
- `apps/api/.env.example` — todas as variáveis e seus defaults seguros.
