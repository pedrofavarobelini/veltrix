/**
 * Classificação dos providers na interface
 * (PEDROCORE-UX-V1 · modo DEV e correção de catálogo em
 * PEDROCORE-V1-FINAL-UI-FIX).
 *
 * TRÊS ESTADOS DISTINTOS, que não devem ser confundidos:
 *
 *   VISÍVEL       é uma IA pública conhecida pelo PedroCore. Aparece nas
 *                 Configurações e no seletor do composer, mesmo sem chave.
 *
 *   CONFIGURADO   o backend tem credencial/configuração para ela. Vem de
 *                 `/api/providers` no campo `configured` — é a única fonte, e
 *                 muda sozinha quando o operador edita o `.env` do backend.
 *
 *   SELECIONÁVEL  pode de fato iniciar uma conversa agora: visível, homologada
 *                 e configurada.
 *
 * A versão anterior deste arquivo colapsou os três em uma lista só
 * (`["gemini"]`), o que sumia com OpenAI, Claude, DeepSeek e Grok da interface
 * e os empurrava para a área de infraestrutura interna — onde não pertencem.
 * São IAs externas conhecidas, apenas ainda indisponíveis.
 *
 * ATENÇÃO — nada aqui é regra de domínio. Nenhum provider é removido do
 * sistema: todos continuam registrados, roteáveis e usados pelo pipeline.
 */

import type { ProviderInfo } from "../services/api";

/**
 * IAs externas públicas que o PedroCore conhece. Sempre VISÍVEIS, com ou sem
 * chave configurada — espelha o `_MODEL_CATALOG`/`provider_catalog` do backend.
 */
export const PUBLIC_AI_PROVIDER_IDS = [
  "gemini",
  "openai",
  "claude",
  "deepseek",
  "grok",
] as const;

/**
 * IAs públicas HOMOLOGADAS para uso real.
 *
 * Espelho de `provider_catalog/service.py`, onde `gemini` é `HOMOLOGATED_REAL`
 * com `authorized_for_auto = True` e os demais são `NOT_HOMOLOGATED`. O
 * contrato público de `/api/providers` ainda não expõe `homologation` — expõe
 * name/label/default_model/configured/real_provider — então a regra fica
 * declarada aqui, em UM lugar, até que o backend a exponha. Quando expuser,
 * este arquivo passa a lê-la e a constante deixa de existir.
 *
 * Homologar um segundo provider é decisão de frente própria, não de UI.
 */
export const HOMOLOGATED_PROVIDER_IDS = ["gemini"] as const;

/**
 * Providers internos que a build de DESENVOLVIMENTO aceita como destino real
 * de conversa. Não são IAs públicas e nunca aparecem na build pública.
 *
 * A lista tem exatamente um item, por razão técnica lida do backend. Um
 * provider só entra aqui se for de fato um destino de chat: precisa devolver
 * texto para uma mensagem arbitrária, sem chamada externa e sem opt-in que a
 * interface não envia.
 *
 *   mock         ENTRA. `MockProvider.generate_response` devolve texto para
 *                qualquer mensagem, `real_provider=False`, `is_configured`
 *                sempre `True`, nenhuma rede, nenhuma chave, nenhum opt-in.
 *
 *   local_qa     FICA FORA. Cai em `LOCAL_PROVIDERS` e nunca chega a um
 *                adapter: o pipeline responde com o resumo do
 *                `qa_text_analyzer` sobre ARTEFATOS. É análise determinística
 *                de release gate, não conversa.
 *
 *   local_model  FICA FORA. `_execute_local_model` exige `allow_local_model`
 *                no payload E `PEDROCORE_ENABLE_LOCAL_MODEL=true` com backend
 *                local. O composer não envia esse opt-in e o default é OFF,
 *                então selecioná-lo produziria fallback Mock silencioso.
 *
 *   auto         FICA FORA. É estratégia de roteamento, não uma IA, e exige
 *                `allow_real_provider=true` para resolver em Gemini.
 */
export const DEV_SELECTABLE_PROVIDER_IDS = ["mock"] as const;

export type PublicAiProviderId = (typeof PUBLIC_AI_PROVIDER_IDS)[number];
export type DevProviderId = (typeof DEV_SELECTABLE_PROVIDER_IDS)[number];

/** `true` somente na build de desenvolvimento (`vite dev`). */
export function isDevBuild(): boolean {
  return import.meta.env.DEV === true;
}

/** É uma IA pública conhecida? Independe de estar configurada. */
export function isPublicAiProviderId(providerId: string): providerId is PublicAiProviderId {
  return (PUBLIC_AI_PROVIDER_IDS as readonly string[]).includes(providerId);
}

/** É homologada para uso real? Independe de estar configurada. */
export function isHomologatedProviderId(providerId: string): boolean {
  return (HOMOLOGATED_PROVIDER_IDS as readonly string[]).includes(providerId);
}

/** É um provider interno liberado em desenvolvimento? */
export function isDevProviderId(providerId: string): providerId is DevProviderId {
  return (DEV_SELECTABLE_PROVIDER_IDS as readonly string[]).includes(providerId);
}

/** Predicado de VISIBILIDADE sobre o objeto vindo de /api/providers. */
export function isPublicAiProvider(provider: ProviderInfo): boolean {
  return isPublicAiProviderId(provider.name);
}

/**
 * Catálogo VISÍVEL: todas as IAs públicas conhecidas, configuradas ou não.
 *
 * A ordem segue `PUBLIC_AI_PROVIDER_IDS` e não a do backend, para que a
 * interface tenha uma sequência estável mesmo se o registry mudar de ordem.
 * Um ID declarado aqui e ausente do catálogo do backend é simplesmente
 * ignorado — a UI nunca inventa provider que o backend não conhece.
 */
export function filterPublicAiProviders(providers: ProviderInfo[]): ProviderInfo[] {
  return PUBLIC_AI_PROVIDER_IDS.map((id) =>
    providers.find((item) => item.name === id),
  ).filter((item): item is ProviderInfo => item !== undefined);
}

/**
 * Infraestrutura interna do pipeline: tudo que não é IA pública.
 *
 * `mock`, `local_qa`, `local_model` e `auto`. Aparece somente na área
 * "Avançado — desenvolvimento", nunca junto das IAs públicas.
 */
export function filterInternalProviders(providers: ProviderInfo[]): ProviderInfo[] {
  return providers.filter((item) => !isPublicAiProvider(item));
}

/**
 * SELECIONÁVEL: pode iniciar uma conversa real agora?
 *
 * Três condições para uma IA pública — visível, homologada e configurada. A
 * checagem de `configured` é o que faz a interface reagir sozinha: basta o
 * operador acrescentar a chave no `.env` do backend para o provider deixar de
 * ficar desabilitado, sem alterar uma linha de frontend.
 *
 * Em desenvolvimento, os internos de `DEV_SELECTABLE_PROVIDER_IDS` também
 * valem — nunca na build pública.
 */
export function isSelectableProvider(provider: ProviderInfo, dev = isDevBuild()): boolean {
  if (dev && isDevProviderId(provider.name)) {
    return true;
  }

  return (
    isPublicAiProviderId(provider.name) &&
    isHomologatedProviderId(provider.name) &&
    provider.configured
  );
}

/** Versão por identificador; precisa do catálogo para consultar `configured`. */
export function isSelectableProviderId(
  providerId: string,
  providers: ProviderInfo[],
  dev = isDevBuild(),
): boolean {
  const provider = providers.find((item) => item.name === providerId);

  return provider !== undefined && isSelectableProvider(provider, dev);
}

/**
 * Motivo curto de indisponibilidade, para o rótulo do seletor. `null` quando o
 * provider está utilizável.
 *
 * Distingue as duas causas em vez de dar uma mensagem única: "não configurado"
 * é acionável pelo operador (basta a chave); "não homologado" não é, e depende
 * de uma frente de homologação.
 */
export function describeUnavailability(
  provider: ProviderInfo,
  dev = isDevBuild(),
): string | null {
  if (isSelectableProvider(provider, dev)) {
    return null;
  }

  if (!provider.configured) {
    return "não configurado";
  }

  return "não homologado";
}

/**
 * O que o composer OFERECE no seletor: as IAs públicas — utilizáveis ou não,
 * porque as indisponíveis aparecem desabilitadas e explicadas — e, apenas em
 * desenvolvimento, os internos aptos a conversar.
 */
export function filterOfferedProviders(
  providers: ProviderInfo[],
  dev = isDevBuild(),
): ProviderInfo[] {
  const publicOnes = filterPublicAiProviders(providers);

  if (!dev) {
    return publicOnes;
  }

  return [...publicOnes, ...providers.filter((item) => isDevProviderId(item.name))];
}
