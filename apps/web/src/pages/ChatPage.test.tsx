import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChatPage } from "./ChatPage";
import * as api from "../services/api";
import { PROVIDER_SETTINGS_STORAGE_KEY } from "../utils/providerSettings";

const CATALOG: api.ProviderInfo[] = [
  { name: "mock", label: "Mock", default_model: "mock-v1", configured: true, real_provider: false },
  { name: "gemini", label: "Gemini", default_model: "gemini-3.5-flash", configured: true, real_provider: true },
  { name: "openai", label: "OpenAI", default_model: "gpt-5.2-mini", configured: false, real_provider: true },
  { name: "claude", label: "Claude", default_model: "claude-sonnet-4-5", configured: false, real_provider: true },
  { name: "deepseek", label: "DeepSeek", default_model: "deepseek-chat", configured: false, real_provider: true },
  { name: "grok", label: "Grok/xAI", default_model: "grok-4.3", configured: false, real_provider: true },
  { name: "local_qa", label: "Local QA", default_model: "local-qa-v1", configured: true, real_provider: false },
  { name: "auto", label: "Auto", default_model: "auto", configured: true, real_provider: true },
];

function chatResponse(overrides: Partial<api.ChatResponse> = {}): api.ChatResponse {
  return {
    answer: "resposta",
    provider: "gemini",
    model: "gemini-3.5-flash",
    mode: "tecnico",
    requested_provider: "gemini",
    fallback_used: false,
    ...overrides,
  };
}

/** Grava preferências como se uma sessão anterior tivesse deixado o F5 pronto. */
function persistSettings(settings: Record<string, unknown>) {
  window.localStorage.setItem(
    PROVIDER_SETTINGS_STORAGE_KEY,
    JSON.stringify({ model: "gemini-3.5-flash", mode: "tecnico", systemPrompt: "p", ...settings }),
  );
}

function composer() {
  return screen.getByLabelText("Mensagem para o Veltrix");
}

describe("ChatPage — seleção de IA e autorização", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.spyOn(api, "getProviders").mockResolvedValue(CATALOG);
    vi.stubGlobal("SpeechRecognition", undefined);
    vi.stubGlobal("webkitSpeechRecognition", undefined);
  });

  it("provider sem semântica de chat avisa e bloqueia o envio", async () => {
    // `local_qa` não é destino de conversa em ambiente algum: o composer deve
    // tratá-lo como "nenhuma IA selecionada".
    persistSettings({ provider: "local_qa", authorizedRealProvider: null });

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    expect(screen.getByText(/Nenhuma IA selecionada/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });

  it("na build de produção o padrão `mock` não conta como IA escolhida", async () => {
    vi.stubEnv("DEV", false);

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    expect(screen.getByText(/Nenhuma IA selecionada/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });

  it("Gemini sem autorização exige ativação em Configurações antes de enviar", async () => {
    persistSettings({ provider: "gemini", authorizedRealProvider: null });

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    fireEvent.change(composer(), { target: { value: "oi" } });

    expect(screen.getByText(/precisa ser ativado em Configurações/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });

  it("a autorização do Gemini sobrevive ao recarregar e libera o envio", async () => {
    persistSettings({ provider: "gemini", authorizedRealProvider: "gemini" });
    const send = vi.spyOn(api, "sendChatMessage").mockResolvedValue(chatResponse());

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    fireEvent.change(composer(), { target: { value: "oi" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() => expect(send).toHaveBeenCalledTimes(1));
    expect(send.mock.calls[0][0].allow_real_provider).toBe(true);
  });

  it("autorização gravada para OUTRO provider não vale para o Gemini", async () => {
    persistSettings({ provider: "gemini", authorizedRealProvider: "openai" });

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    expect(screen.getByText(/precisa ser ativado em Configurações/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });

  it("trocar de IA descarta a autorização anterior", async () => {
    persistSettings({ provider: "gemini", authorizedRealProvider: "gemini" });

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    fireEvent.change(screen.getByLabelText("IA utilizada nesta conversa"), {
      target: { value: "mock" },
    });
    fireEvent.change(screen.getByLabelText("IA utilizada nesta conversa"), {
      target: { value: "gemini" },
    });

    expect(screen.getByText(/precisa ser ativado em Configurações/)).toBeInTheDocument();
  });

  it("o composer não oferece providers internos sem semântica de chat", async () => {
    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    const options = screen
      .getAllByRole("option")
      .map((item) => (item as HTMLOptionElement).value);

    expect(options).toContain("gemini");
    expect(options).not.toContain("local_qa");
    expect(options).not.toContain("auto");
  });

  it("o composer lista as cinco IAs públicas, configuradas ou não", async () => {
    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    const options = screen
      .getAllByRole("option")
      .map((item) => (item as HTMLOptionElement).value);

    for (const publica of ["gemini", "openai", "claude", "deepseek", "grok"]) {
      expect(options).toContain(publica);
    }
  });

  it("IA pública sem chave aparece desabilitada no seletor", async () => {
    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    for (const label of [
      "OpenAI — não configurado",
      "Claude — não configurado",
      "DeepSeek — não configurado",
      "Grok/xAI — não configurado",
    ]) {
      expect(screen.getByRole("option", { name: label })).toBeDisabled();
    }

    expect(screen.getByRole("option", { name: "Gemini" })).toBeEnabled();
  });

  it("IA pública sem chave não permite envio e explica o motivo real", async () => {
    persistSettings({ provider: "openai", authorizedRealProvider: "openai" });

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    expect(screen.getByText(/OpenAI não está disponível/)).toBeInTheDocument();
    expect(screen.getByText(/configure a credencial no \.env do backend/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });

  it("Gemini sem chave no backend deixa de ser selecionável", async () => {
    vi.mocked(api.getProviders).mockResolvedValue(
      CATALOG.map((item) =>
        item.name === "gemini" ? { ...item, configured: false } : item,
      ),
    );
    persistSettings({ provider: "gemini", authorizedRealProvider: "gemini" });

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    expect(screen.getByText(/Gemini não está disponível/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });
});

describe("ChatPage — Configurações", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.spyOn(api, "getProviders").mockResolvedValue(CATALOG);
    vi.stubGlobal("SpeechRecognition", undefined);
    vi.stubGlobal("webkitSpeechRecognition", undefined);
  });

  async function openSettings() {
    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: /Configurações/ }));
    await screen.findByRole("dialog");
  }

  it("mostra as cinco IAs públicas em Provedores de IA, mesmo sem chave", async () => {
    await openSettings();

    const dialog = screen.getByRole("dialog");

    for (const label of ["Gemini", "OpenAI", "Claude", "DeepSeek", "Grok/xAI"]) {
      expect(within(dialog).getByText(label)).toBeInTheDocument();
    }
  });

  it("marca as IAs sem chave como não configuradas e não clicáveis", async () => {
    await openSettings();

    const dialog = screen.getByRole("dialog");

    expect(within(dialog).getAllByText("Não configurado")).toHaveLength(4);
    expect(within(dialog).getByText("Configurado")).toBeInTheDocument();

    const openaiCard = within(dialog).getByText("OpenAI").closest("button");
    expect(openaiCard).toBeDisabled();

    const geminiCard = within(dialog).getByText("Gemini").closest("button");
    expect(geminiCard).toBeEnabled();
  });

  it("não coloca IA pública na área de infraestrutura interna", async () => {
    await openSettings();

    const dialog = screen.getByRole("dialog");
    const advanced = dialog.querySelector(".internal-provider-list");

    expect(advanced).not.toBeNull();
    expect(advanced?.textContent).toContain("Mock");
    expect(advanced?.textContent).toContain("Local QA");
    expect(advanced?.textContent).toContain("Auto");

    for (const publica of ["OpenAI", "Claude", "DeepSeek", "Grok"]) {
      expect(advanced?.textContent).not.toContain(publica);
    }
  });
});

describe("ChatPage — provider interno em desenvolvimento", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.spyOn(api, "getProviders").mockResolvedValue(CATALOG);
    vi.stubGlobal("SpeechRecognition", undefined);
    vi.stubGlobal("webkitSpeechRecognition", undefined);
  });

  it("envia para o mock sem exigir autorização, marcando o ambiente técnico", async () => {
    persistSettings({ provider: "mock", authorizedRealProvider: null });
    const send = vi.spyOn(api, "sendChatMessage").mockResolvedValue(
      chatResponse({ provider: "mock", model: "mock-v1", requested_provider: "mock" }),
    );

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    expect(screen.getByText("DEV")).toBeInTheDocument();
    expect(screen.getByText(/Ambiente técnico de desenvolvimento/)).toBeInTheDocument();

    fireEvent.change(composer(), { target: { value: "oi" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    // Este é exatamente o defeito corrigido: antes o drawer oferecia o provider
    // interno e o composer travava o envio sem autorização possível.
    await waitFor(() => expect(send).toHaveBeenCalledTimes(1));
    expect(send.mock.calls[0][0].provider).toBe("mock");
    expect(send.mock.calls[0][0].allow_real_provider).toBe(false);
  });

  it("na build de produção o mock deixa de ser oferecido", async () => {
    vi.stubEnv("DEV", false);
    persistSettings({ provider: "mock", authorizedRealProvider: null });

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    const options = screen
      .getAllByRole("option")
      .map((item) => (item as HTMLOptionElement).value);

    expect(options).not.toContain("mock");
    expect(screen.queryByText("DEV")).toBeNull();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });
});

describe("ChatPage — verdade sobre quem respondeu", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.spyOn(api, "getProviders").mockResolvedValue(CATALOG);
    vi.stubGlobal("SpeechRecognition", undefined);
    vi.stubGlobal("webkitSpeechRecognition", undefined);
  });

  async function sendWithGemini(response: api.ChatResponse) {
    persistSettings({ provider: "gemini", authorizedRealProvider: "gemini" });
    const send = vi.spyOn(api, "sendChatMessage").mockResolvedValue(response);

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    fireEvent.change(composer(), {
      target: { value: "Me fale o que foi feito recentemente no sistema." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));
    await waitFor(() => expect(send).toHaveBeenCalledTimes(1));

    return send;
  }

  // (B) IA real explicitamente escolhida: o Veltrix proíbe a degradação
  // silenciosa para Mock no PRÓPRIO chat, pelo campo que já existe no contrato.
  it("escolha explícita de IA real proíbe o fallback Mock silencioso", async () => {
    const send = await sendWithGemini(chatResponse());

    expect(send.mock.calls[0][0].allow_real_provider).toBe(true);
    expect(send.mock.calls[0][0].allow_mock_fallback).toBe(false);
  });

  // (C) Gemini respondeu: provider efetivo Gemini, sem fallback, sem alarme.
  it("resposta do Gemini aparece como resposta do Gemini", async () => {
    await sendWithGemini(
      chatResponse({ answer: "Resposta real do Gemini.", provider: "gemini" }),
    );

    expect(await screen.findByText("Resposta real do Gemini.")).toBeInTheDocument();
    expect(screen.queryByText(/não concluiu a solicitação/)).toBeNull();
    expect(screen.queryByText(/fallback local usado/)).toBeNull();
  });

  // (D) Gemini falhou: a UI não pode mentir dizendo que a IA respondeu.
  it("falha do Gemini é mostrada como falha do Gemini, não como resposta", async () => {
    await sendWithGemini(
      chatResponse({
        answer: "Não foi possível concluir a solicitação com o provider selecionado.",
        provider: "none",
        model: "none",
        fallback_used: false,
        status: "blocked",
        error: "falha interna do provider",
      }),
    );

    expect(
      await screen.findByText("Gemini não concluiu a solicitação."),
    ).toBeInTheDocument();
    expect(screen.getByText("Gemini falhou")).toBeInTheDocument();
    // Nenhuma afordância de opinião sobre uma resposta que não existiu.
    expect(screen.queryByRole("button", { name: "Gostei" })).toBeNull();
  });

  // (H) Chat geral nunca recebe disclaimer financeiro.
  it("chat geral não exibe disclaimer financeiro na falha", async () => {
    await sendWithGemini(
      chatResponse({
        answer: "Não foi possível concluir a solicitação com o provider selecionado.",
        provider: "none",
        model: "none",
        status: "blocked",
      }),
    );

    await screen.findByText("Gemini não concluiu a solicitação.");
    expect(screen.queryByText(/ação financeira/)).toBeNull();
    expect(screen.queryByText(/altera seus dados/)).toBeNull();
  });

  // (A) Sem consentimento não há nem requisição: o envio segue bloqueado, e o
  // provider interno de desenvolvimento mantém o fallback local disponível.
  it("provider interno mantém o fallback local permitido", async () => {
    persistSettings({ provider: "mock", authorizedRealProvider: null });
    const send = vi.spyOn(api, "sendChatMessage").mockResolvedValue(
      chatResponse({ provider: "mock", model: "mock-v1", requested_provider: "mock" }),
    );

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    fireEvent.change(composer(), { target: { value: "oi" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() => expect(send).toHaveBeenCalledTimes(1));
    expect(send.mock.calls[0][0].allow_mock_fallback).toBe(true);
  });
});

describe("ChatPage — anexos", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.spyOn(api, "getProviders").mockResolvedValue(CATALOG);
    vi.stubGlobal("SpeechRecognition", undefined);
    vi.stubGlobal("webkitSpeechRecognition", undefined);
    persistSettings({ provider: "gemini", authorizedRealProvider: "gemini" });
  });

  async function attach(file: File) {
    fireEvent.change(document.getElementById("composer-attachment-input") as HTMLInputElement, {
      target: { files: [file] },
    });
  }

  it("anexa um arquivo válido e envia como artefato do contrato existente", async () => {
    const send = vi.spyOn(api, "sendChatMessage").mockResolvedValue(chatResponse());

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    await attach(new File(["# Relatório"], "notas.md", { type: "text/markdown" }));
    await screen.findByText("notas.md");

    fireEvent.change(composer(), { target: { value: "resuma" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() => expect(send).toHaveBeenCalledTimes(1));
    expect(send.mock.calls[0][0].artifacts).toEqual([
      { type: "markdown", name: "notas.md", content: "# Relatório" },
    ]);
  });

  it("recusa arquivo fora da allowlist e não o adiciona", async () => {
    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    await attach(new File(["binario"], "foto.png", { type: "image/png" }));

    expect(await screen.findByText(/Formato não suportado/)).toBeInTheDocument();
    expect(screen.queryByText("foto.png")).toBeNull();
  });

  it("limpa os anexos após envio bem-sucedido", async () => {
    vi.spyOn(api, "sendChatMessage").mockResolvedValue(chatResponse());

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    await attach(new File(["linha"], "app.log", { type: "text/plain" }));
    await screen.findByText("app.log");

    fireEvent.change(composer(), { target: { value: "analise" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() => expect(screen.queryByText("app.log")).toBeNull());
  });

  it("mantém os anexos quando o envio falha, para permitir reenvio", async () => {
    vi.spyOn(api, "sendChatMessage").mockRejectedValue(new Error("rede"));

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    await attach(new File(["linha"], "app.log", { type: "text/plain" }));
    await screen.findByText("app.log");

    fireEvent.change(composer(), { target: { value: "analise" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() => expect(api.sendChatMessage).toHaveBeenCalled());
    expect(screen.getByText("app.log")).toBeInTheDocument();
  });

  it("mensagem só com anexo envia texto não vazio, respeitando min_length do backend", async () => {
    const send = vi.spyOn(api, "sendChatMessage").mockResolvedValue(chatResponse());

    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    await attach(new File(["a,b"], "dados.csv", { type: "text/csv" }));
    await screen.findByText("dados.csv");

    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() => expect(send).toHaveBeenCalledTimes(1));
    expect(send.mock.calls[0][0].message.length).toBeGreaterThan(0);
    expect(send.mock.calls[0][0].message).toContain("dados.csv");
  });

  it("remove um anexo antes do envio", async () => {
    render(<ChatPage />);
    await waitFor(() => expect(api.getProviders).toHaveBeenCalled());

    await attach(new File(["texto"], "notas.txt", { type: "text/plain" }));
    await screen.findByText("notas.txt");

    fireEvent.click(screen.getByRole("button", { name: "Remover anexo notas.txt" }));

    await waitFor(() => expect(screen.queryByText("notas.txt")).toBeNull());
  });
});
