export type ProviderSettings = {
  provider: string;
  model: string;
  mode: string;
  systemPrompt: string;
  /**
   * Identificador do provider real cujo uso o usuário autorizou NESTE navegador.
   * `null` quando não há autorização vigente.
   *
   * É consentimento, não credencial: nunca guarda chave, token ou secret. As
   * credenciais permanecem exclusivamente no backend. Guardamos o ID e não um
   * booleano global justamente para que a autorização não vaze de um provider
   * para outro (princípio de menor privilégio).
   */
  authorizedRealProvider: string | null;
};

export const PROVIDER_SETTINGS_STORAGE_KEY = "pedrocore:v5:provider-settings";

function canUseLocalStorage() {
  return typeof window !== "undefined" && Boolean(window.localStorage);
}

/**
 * Valida apenas os campos que sempre existiram. `authorizedRealProvider` é
 * opcional de propósito: payloads gravados antes desta versão continuam
 * válidos e são lidos como "sem autorização".
 */
function isProviderSettings(value: unknown): value is Partial<ProviderSettings> {
  if (!value || typeof value !== "object") {
    return false;
  }

  const item = value as Partial<ProviderSettings>;

  return (
    typeof item.provider === "string" &&
    typeof item.model === "string" &&
    typeof item.mode === "string" &&
    typeof item.systemPrompt === "string"
  );
}

/** Normaliza o consentimento persistido; qualquer coisa fora do formato vira `null`. */
function normalizeAuthorizedRealProvider(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  return value.trim() || null;
}

export function loadProviderSettings(defaultSettings: ProviderSettings): ProviderSettings {
  if (!canUseLocalStorage()) {
    return defaultSettings;
  }

  try {
    const rawSettings = window.localStorage.getItem(PROVIDER_SETTINGS_STORAGE_KEY);

    if (!rawSettings) {
      return defaultSettings;
    }

    const parsedSettings = JSON.parse(rawSettings);

    if (!isProviderSettings(parsedSettings)) {
      return defaultSettings;
    }

    return {
      provider: parsedSettings.provider?.trim() || defaultSettings.provider,
      model: parsedSettings.model?.trim() || defaultSettings.model,
      mode: parsedSettings.mode?.trim() || defaultSettings.mode,
      systemPrompt: parsedSettings.systemPrompt?.trim() || defaultSettings.systemPrompt,
      authorizedRealProvider: normalizeAuthorizedRealProvider(
        parsedSettings.authorizedRealProvider,
      ),
    };
  } catch {
    return defaultSettings;
  }
}

export function saveProviderSettings(settings: ProviderSettings) {
  if (!canUseLocalStorage()) {
    return;
  }

  try {
    window.localStorage.setItem(PROVIDER_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // localStorage pode falhar por quota, modo privado ou bloqueio do navegador.
  }
}
