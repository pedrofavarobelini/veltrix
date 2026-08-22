# Contribuindo com o PedroCore IA

Projeto pessoal, mantido por uma pessoa. O processo aqui é curto de propósito:
o suficiente para que uma contribuição seja avaliável, e nada além disso.

## Setup

Pré-requisitos: Python 3.12+, Node 22+.

```bash
# Backend
cd apps/api
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/macOS: source .venv/bin/activate
pip install -e .
cp .env.example .env      # funciona sem nenhuma chave: o padrão é `mock`

# Frontend
cd apps/web
npm install
```

Rodar:

```bash
cd apps/api && python -m uvicorn app.main:app --reload --port 3333
cd apps/web && npm run dev
```

## Testes

Tudo abaixo precisa passar antes de abrir um PR:

```bash
cd apps/api && python -m pytest -q
cd apps/web && npm test && npm run typecheck && npm run build
```

Se você mexeu em documentação dentro de `PedroCore IA/`, valide o grafo:

```bash
cd apps/api && python -m app.modules.docs_graph.service
```

Ele falha diante de órfão, link quebrado, link ambíguo, basename duplicado ou
documento inalcançável a partir do MOC raiz. Um documento novo precisa estar
linkado a partir de algum MOC.

## Estilo

- **Backend:** Python com type hints, módulos por responsabilidade em
  `app/modules/<dominio>/` com `schemas.py` + `service.py`. `ruff` para lint.
- **Frontend:** TypeScript estrito, componentes funcionais, sem state manager
  externo. Lógica de domínio fica em `utils/` e `hooks/`, não dentro do JSX.
- **Comentários** explicam *por que*, não *o que*. Se o código já diz o que
  faz, o comentário deve dizer a razão da decisão — especialmente quando é uma
  restrição de segurança ou um limite espelhando o backend.
- **Idioma:** documentação e comentários em português; identificadores de
  código em inglês, seguindo o que já existe.
- Siga o estilo do arquivo que você está editando. Consistência local vale mais
  que preferência pessoal.

## Segurança

Estas regras não são negociáveis:

- **Nunca** commite `.env`, chave, token ou credencial. Se precisar de uma
  variável nova, adicione-a a `.env.example` com valor **vazio** e um
  comentário explicando para que serve.
- **Nunca** faça o frontend guardar credencial. Chaves são exclusividade do
  backend.
- Recursos com custo, rede ou efeito externo entram **default OFF**, atrás de
  flag explícita.
- Não afrouxe safe mode, matriz de autorização, limites de artefato ou guards
  de OCR/multimodal/Playwright sem uma frente própria que justifique.
- Encontrou uma vulnerabilidade? Não abra issue pública — siga
  [`SECURITY.md`](SECURITY.md).

## Pull requests

- Uma mudança por PR. PR pequeno é revisado; PR grande é adiado.
- Descreva **o problema** e a razão da abordagem, não só o diff.
- Inclua teste para comportamento novo ou corrigido. O teste deve falhar sem a
  sua mudança.
- Não quebre contrato de API. `/api/chat`, `/api/orchestrate`, `ChatRequest`,
  `ChatResponse`, os contratos FinGuard/Structa e o registry de providers são
  **congelados**: mudanças precisam ser aditivas e retrocompatíveis. Se algo
  destrutivo parecer necessário, abra uma issue antes de implementar.
- Não crie tags nem altere versões em um PR de funcionalidade.
- Atualize a documentação junto do código. Código e documentação divergentes
  são tratados como defeito.

## O que provavelmente não será aceito

- Trocar framework, arquitetura central ou introduzir state manager.
- Adicionar dependência com versão `"latest"` — use versão exata.
- Habilitar provider real, rede ou custo externo por padrão.
- Refatoração ampla sem problema concreto associado.
