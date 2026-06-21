export type ProviderSettings = {
  provider: string;
  model: string;
  mode: string;
  systemPrompt: string;
};

export const PROVIDER_SETTINGS_STORAGE_KEY = "pedrocore:v5:provider-settings";

function canUseLocalStorage() {
  return typeof window !== "undefined" && Boolean(window.localStorage);
}

function isProviderSettings(value: unknown): value is ProviderSettings {
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
      provider: parsedSettings.provider.trim() || defaultSettings.provider,
      model: parsedSettings.model.trim() || defaultSettings.model,
      mode: parsedSettings.mode.trim() || defaultSettings.mode,
      systemPrompt: parsedSettings.systemPrompt.trim() || defaultSettings.systemPrompt,
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
