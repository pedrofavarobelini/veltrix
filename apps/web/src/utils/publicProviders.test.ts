import { describe, expect, it } from "vitest";
import type { ProviderInfo } from "../services/api";
import {
  DEV_SELECTABLE_PROVIDER_IDS,
  HOMOLOGATED_PROVIDER_IDS,
  PUBLIC_AI_PROVIDER_IDS,
  describeUnavailability,
  filterInternalProviders,
  filterOfferedProviders,
  filterPublicAiProviders,
  isDevProviderId,
  isHomologatedProviderId,
  isPublicAiProviderId,
  isSelectableProvider,
  isSelectableProviderId,
} from "./publicProviders";

/**
 * Catálogo equivalente ao que `/api/providers` devolve. Só o Gemini aparece
 * como `configured`, que é o estado real do ambiente homologado.
 */
const CATALOG: ProviderInfo[] = [
  { name: "mock", label: "Mock", default_model: "mock-v1", configured: true, real_provider: false },
  { name: "gemini", label: "Gemini", default_model: "gemini-3.5-flash", configured: true, real_provider: true },
  { name: "openai", label: "OpenAI", default_model: "gpt-5.2-mini", configured: false, real_provider: true },
  { name: "claude", label: "Claude", default_model: "claude-sonnet-4-5", configured: false, real_provider: true },
  { name: "deepseek", label: "DeepSeek", default_model: "deepseek-chat", configured: false, real_provider: true },
  { name: "grok", label: "Grok/xAI", default_model: "grok-4.3", configured: false, real_provider: true },
  { name: "local_model", label: "Local Model", default_model: "local", configured: false, real_provider: false },
  { name: "local_qa", label: "Local QA", default_model: "local-qa-v1", configured: true, real_provider: false },
  { name: "auto", label: "Auto", default_model: "auto", configured: true, real_provider: true },
];

function find(name: string): ProviderInfo {
  const provider = CATALOG.find((item) => item.name === name);

  if (!provider) {
    throw new Error(`provider ausente do catálogo de teste: ${name}`);
  }

  return provider;
}

describe("catálogo VISÍVEL de IAs públicas", () => {
  it("declara as cinco IAs externas conhecidas", () => {
    expect([...PUBLIC_AI_PROVIDER_IDS]).toEqual([
      "gemini",
      "openai",
      "claude",
      "deepseek",
      "grok",
    ]);
  });

  it.each(["gemini", "openai", "claude", "deepseek", "grok"])(
    "%s aparece no catálogo público",
    (name) => {
      expect(isPublicAiProviderId(name)).toBe(true);
      expect(filterPublicAiProviders(CATALOG).map((item) => item.name)).toContain(name);
    },
  );

  it("mantém IA pública visível mesmo sem estar configurada", () => {
    const visible = filterPublicAiProviders(CATALOG);

    expect(visible.map((item) => item.name)).toContain("openai");
    expect(find("openai").configured).toBe(false);
  });

  it("apresenta as IAs em ordem estável, independente da ordem do backend", () => {
    const embaralhado = [...CATALOG].reverse();

    expect(filterPublicAiProviders(embaralhado).map((item) => item.name)).toEqual([
      "gemini",
      "openai",
      "claude",
      "deepseek",
      "grok",
    ]);
  });

  it("nunca inventa provider que o backend não conhece", () => {
    const catalogoParcial = [find("gemini"), find("mock")];

    expect(filterPublicAiProviders(catalogoParcial).map((item) => item.name)).toEqual([
      "gemini",
    ]);
  });
});

describe("infraestrutura interna", () => {
  it.each(["mock", "local_qa", "local_model", "auto"])(
    "%s NÃO pertence ao catálogo público",
    (name) => {
      expect(isPublicAiProviderId(name)).toBe(false);
      expect(filterPublicAiProviders(CATALOG).map((item) => item.name)).not.toContain(name);
    },
  );

  it("agrupa exatamente os quatro internos", () => {
    expect(filterInternalProviders(CATALOG).map((item) => item.name)).toEqual([
      "mock",
      "local_model",
      "local_qa",
      "auto",
    ]);
  });

  it("não empurra IA pública para a área interna", () => {
    const internos = filterInternalProviders(CATALOG).map((item) => item.name);

    for (const publica of ["gemini", "openai", "claude", "deepseek", "grok"]) {
      expect(internos).not.toContain(publica);
    }
  });
});

describe("SELECIONÁVEL — visível, homologado e configurado", () => {
  it("declara apenas o Gemini como homologado", () => {
    expect([...HOMOLOGATED_PROVIDER_IDS]).toEqual(["gemini"]);
    expect(isHomologatedProviderId("gemini")).toBe(true);
    expect(isHomologatedProviderId("openai")).toBe(false);
  });

  it("Gemini configurado permanece selecionável", () => {
    expect(isSelectableProvider(find("gemini"), false)).toBe(true);
  });

  it("Gemini sem chave deixa de ser selecionável, mas continua visível", () => {
    const semChave: ProviderInfo = { ...find("gemini"), configured: false };

    expect(isSelectableProvider(semChave, false)).toBe(false);
    expect(isPublicAiProviderId(semChave.name)).toBe(true);
  });

  it.each(["openai", "claude", "deepseek", "grok"])(
    "%s não configurado não permite envio real",
    (name) => {
      expect(isSelectableProvider(find(name), false)).toBe(false);
      expect(isSelectableProvider(find(name), true)).toBe(false);
    },
  );

  it("provider configurado mas não homologado continua indisponível", () => {
    const configuradoSemHomologacao: ProviderInfo = { ...find("openai"), configured: true };

    expect(isSelectableProvider(configuradoSemHomologacao, false)).toBe(false);
    expect(describeUnavailability(configuradoSemHomologacao, false)).toBe("não homologado");
  });

  it("distingue o motivo da indisponibilidade", () => {
    expect(describeUnavailability(find("openai"), false)).toBe("não configurado");
    expect(describeUnavailability(find("gemini"), false)).toBeNull();
  });

  it("a versão por identificador consulta o catálogo", () => {
    expect(isSelectableProviderId("gemini", CATALOG, false)).toBe(true);
    expect(isSelectableProviderId("openai", CATALOG, false)).toBe(false);
    expect(isSelectableProviderId("inexistente", CATALOG, false)).toBe(false);
  });

  it("reage sozinha quando o backend passa a reportar configured=true", () => {
    // Fluxo real: operador adiciona a chave no .env, /api/providers muda, e o
    // frontend habilita o provider sem alteração de código.
    const antes = CATALOG;
    const depois = CATALOG.map((item) =>
      item.name === "openai" ? { ...item, configured: true } : item,
    );

    expect(isSelectableProviderId("openai", antes, false)).toBe(false);
    // Continua bloqueado só pela homologação, não mais pela configuração.
    expect(describeUnavailability(find("openai"), false)).toBe("não configurado");
    expect(
      describeUnavailability(
        depois.find((item) => item.name === "openai") as ProviderInfo,
        false,
      ),
    ).toBe("não homologado");
  });
});

describe("modo DEV", () => {
  it("libera apenas o mock como provider interno de conversa", () => {
    expect([...DEV_SELECTABLE_PROVIDER_IDS]).toEqual(["mock"]);
    expect(isDevProviderId("mock")).toBe(true);
  });

  it("Mock DEV continua preservado", () => {
    expect(isSelectableProvider(find("mock"), true)).toBe(true);
  });

  it("build pública não transforma Mock em IA pública", () => {
    expect(isSelectableProvider(find("mock"), false)).toBe(false);
    expect(isPublicAiProviderId("mock")).toBe(false);
    expect(filterOfferedProviders(CATALOG, false).map((item) => item.name)).not.toContain(
      "mock",
    );
  });

  it("mantém local_qa, local_model e auto fora do composer mesmo em DEV", () => {
    const oferecidos = filterOfferedProviders(CATALOG, true).map((item) => item.name);

    expect(oferecidos).not.toContain("local_qa");
    expect(oferecidos).not.toContain("local_model");
    expect(oferecidos).not.toContain("auto");
  });

  it("o seletor oferece as IAs públicas e, em DEV, o mock ao final", () => {
    expect(filterOfferedProviders(CATALOG, false).map((item) => item.name)).toEqual([
      "gemini",
      "openai",
      "claude",
      "deepseek",
      "grok",
    ]);
    expect(filterOfferedProviders(CATALOG, true).map((item) => item.name)).toEqual([
      "gemini",
      "openai",
      "claude",
      "deepseek",
      "grok",
      "mock",
    ]);
  });

  it("nenhum interno sem semântica de chat vira destino, em ambiente algum", () => {
    for (const interno of ["local_qa", "local_model", "auto"]) {
      expect(isSelectableProviderId(interno, CATALOG, true)).toBe(false);
      expect(isSelectableProviderId(interno, CATALOG, false)).toBe(false);
    }
  });
});
