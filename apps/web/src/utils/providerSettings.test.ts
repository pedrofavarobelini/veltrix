import { beforeEach, describe, expect, it } from "vitest";
import {
  PROVIDER_SETTINGS_STORAGE_KEY,
  loadProviderSettings,
  saveProviderSettings,
} from "./providerSettings";
import type { ProviderSettings } from "./providerSettings";

const DEFAULTS: ProviderSettings = {
  provider: "mock",
  model: "mock-v1",
  mode: "tecnico",
  systemPrompt: "prompt base",
  authorizedRealProvider: null,
};

describe("persistência das preferências de provider", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("a autorização do Gemini sobrevive ao recarregar a página", () => {
    saveProviderSettings({ ...DEFAULTS, provider: "gemini", authorizedRealProvider: "gemini" });

    // Um novo `load` é exatamente o que acontece depois do F5.
    expect(loadProviderSettings(DEFAULTS).authorizedRealProvider).toBe("gemini");
  });

  it("guarda o ID do provider autorizado, nunca um booleano global", () => {
    saveProviderSettings({ ...DEFAULTS, provider: "gemini", authorizedRealProvider: "gemini" });

    const raw = JSON.parse(window.localStorage.getItem(PROVIDER_SETTINGS_STORAGE_KEY) ?? "{}");

    expect(raw.authorizedRealProvider).toBe("gemini");
    expect(typeof raw.authorizedRealProvider).not.toBe("boolean");
  });

  it("nunca grava chave de API no navegador", () => {
    saveProviderSettings({ ...DEFAULTS, provider: "gemini", authorizedRealProvider: "gemini" });

    const raw = window.localStorage.getItem(PROVIDER_SETTINGS_STORAGE_KEY) ?? "";

    expect(raw.toLowerCase()).not.toContain("api_key");
    expect(raw.toLowerCase()).not.toContain("apikey");
    expect(raw.toLowerCase()).not.toContain("secret");
    expect(raw.toLowerCase()).not.toContain("token");
  });

  it("lê payload antigo, sem o campo de autorização, como sem autorização", () => {
    window.localStorage.setItem(
      PROVIDER_SETTINGS_STORAGE_KEY,
      JSON.stringify({ provider: "gemini", model: "g", mode: "tecnico", systemPrompt: "p" }),
    );

    expect(loadProviderSettings(DEFAULTS).authorizedRealProvider).toBeNull();
  });

  it("normaliza autorização com formato inválido para ausência de autorização", () => {
    for (const invalid of [true, 1, {}, [], "   "]) {
      window.localStorage.setItem(
        PROVIDER_SETTINGS_STORAGE_KEY,
        JSON.stringify({
          provider: "gemini",
          model: "g",
          mode: "tecnico",
          systemPrompt: "p",
          authorizedRealProvider: invalid,
        }),
      );

      expect(loadProviderSettings(DEFAULTS).authorizedRealProvider).toBeNull();
    }
  });

  it("cai no default quando o conteúdo armazenado não é JSON válido", () => {
    window.localStorage.setItem(PROVIDER_SETTINGS_STORAGE_KEY, "{{{ não é json");

    expect(loadProviderSettings(DEFAULTS)).toEqual(DEFAULTS);
  });
});
