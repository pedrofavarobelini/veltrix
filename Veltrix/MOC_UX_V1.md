# MOC UX V1 — Interface pública do Veltrix

Mapa das frentes `PEDROCORE-V1-FINAL-CLOSURE` e `PEDROCORE-V1-FINAL-UI-FIX`,
que fecharam a interface pública do Veltrix: composer único, Configurações
em drawer, catálogo correto das IAs públicas, infraestrutura interna isolada,
ditado por voz e anexos textuais reais.

Estado: **homologado**. Versão de produto V5.2.0; frontend `117 passed`.

Voltar para a entrada do vault: [[MOC_VELTRIX]].

## Fechamento da frente

- [[20-ux-v1/PEDROCORE_V1_FINAL_CLOSURE_01]] — relatório final, veredito,
  gates de teste/segurança/arquitetura e pendências verdadeiras.

## Interface

- [[20-ux-v1/UX_COMPOSER_V1]] — composer, seletor de IA, drawer de
  Configurações, persistência da autorização e acessibilidade.
- [[20-ux-v1/VOZ_E_ANEXOS]] — ditado por voz e anexos textuais: fluxo,
  estados, limites e privacidade.

## Providers

- [[20-ux-v1/PROVIDERS_MODO_DEV]] — os três estados (visível, configurado,
  selecionável); por que as cinco IAs públicas aparecem mesmo sem chave; por que
  só `gemini` está habilitado hoje; por que só `mock` é liberado em
  desenvolvimento; e por que `auto`, `local_qa` e `local_model` não são destinos
  de conversa.

## Qualidade e risco

- [[20-ux-v1/TESTES_FRONTEND]] — stack Vitest, cobertura e números reais.
- [[20-ux-v1/MODELO_DE_AMEACA]] — cenários A/B/C/D e o que falta para expor a
  API na internet.

## Adiado formalmente

- [[20-ux-v1/V2_MULTIMODAL]] — imagem, PDF e DOCX: estado atual, lacunas e a
  arquitetura que a V2 precisa construir.

## Relacionados

- [[MOC_SEGURANCA]] — safe mode, policy, providers reais e limites.
- [[MOC_TESTES]] — suíte backend, suíte frontend e testes opt-in.
- [[MOC_ARQUITETURA]] — camadas, endpoints e módulos.
- [[MOC_VERSOES_STATUS]] — versões, tags e status.
