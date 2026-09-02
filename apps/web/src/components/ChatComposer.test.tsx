import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChatComposer } from "./ChatComposer";
import type { ProviderInfo } from "../services/api";
import type { TextAttachment } from "../utils/attachments";

const GEMINI: ProviderInfo = {
  name: "gemini",
  label: "Gemini",
  default_model: "gemini-3.5-flash",
  configured: true,
  real_provider: true,
};

const MOCK: ProviderInfo = {
  name: "mock",
  label: "Mock",
  default_model: "mock-v1",
  configured: true,
  real_provider: false,
};

const OPENAI: ProviderInfo = {
  name: "openai",
  label: "OpenAI",
  default_model: "gpt-5.2-mini",
  configured: false,
  real_provider: true,
};

type Overrides = Partial<React.ComponentProps<typeof ChatComposer>>;

function renderComposer(overrides: Overrides = {}) {
  const props = {
    value: "",
    loading: false,
    placeholder: "Digite sua mensagem...",
    offeredProviders: [GEMINI],
    provider: "gemini",
    providerIsSelectable: true,
    providerIsDev: false,
    notice: "",
    canSend: true,
    attachments: [] as TextAttachment[],
    onChange: vi.fn(),
    onProviderChange: vi.fn(),
    onSend: vi.fn(),
    onAttachmentsSelected: vi.fn(),
    onAttachmentRemove: vi.fn(),
    ...overrides,
  };

  render(<ChatComposer {...props} />);

  return props;
}

function makeRecognitionInstance() {
  return {
    lang: "",
    continuous: false,
    interimResults: false,
    start: vi.fn(),
    stop: vi.fn(),
    abort: vi.fn(),
    onresult: null as ((event: unknown) => void) | null,
    onerror: null as ((event: { error?: string }) => void) | null,
    onend: null as (() => void) | null,
  };
}

/**
 * Construtor falso da Web Speech API.
 *
 * Precisa ser `function`, não arrow: o hook usa `new Constructor()` e arrow
 * function não é construtível. Retornando um objeto, `new` devolve esse objeto,
 * então o teste mantém a referência para disparar os callbacks.
 */
function stubSpeechRecognition(globalName = "SpeechRecognition") {
  const instance = makeRecognitionInstance();

  vi.stubGlobal(globalName, function SpeechRecognitionStub() {
    return instance;
  });

  return instance;
}

describe("composer — textarea e envio", () => {
  it("Enter envia a mensagem", () => {
    const props = renderComposer({ value: "olá" });

    fireEvent.keyDown(screen.getByLabelText("Mensagem para o Veltrix"), { key: "Enter" });

    expect(props.onSend).toHaveBeenCalledTimes(1);
  });

  it("Shift+Enter quebra a linha em vez de enviar", () => {
    const props = renderComposer({ value: "olá" });

    fireEvent.keyDown(screen.getByLabelText("Mensagem para o Veltrix"), {
      key: "Enter",
      shiftKey: true,
    });

    expect(props.onSend).not.toHaveBeenCalled();
  });

  it("não envia com o textarea vazio, nem por Enter nem pelo botão", () => {
    const props = renderComposer({ value: "   " });

    fireEvent.keyDown(screen.getByLabelText("Mensagem para o Veltrix"), { key: "Enter" });

    expect(props.onSend).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });

  it("bloqueia o envio quando o pai nega (autorização faltando)", () => {
    renderComposer({ value: "olá", canSend: false });

    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });

  it("mostra o estado de carregamento e desabilita o textarea", () => {
    renderComposer({ value: "olá", loading: true, canSend: false });

    expect(screen.getByRole("button", { name: "Enviando..." })).toBeDisabled();
    expect(screen.getByLabelText("Mensagem para o Veltrix")).toBeDisabled();
  });

  it("permite enviar só com anexo, sem texto digitado", () => {
    renderComposer({
      value: "",
      attachments: [
        { id: "1", name: "notas.md", size: 100, artifactType: "markdown", content: "# t" },
      ],
    });

    expect(screen.getByRole("button", { name: "Enviar" })).toBeEnabled();
  });

  it("exibe o aviso de bloqueio vindo do pai", () => {
    renderComposer({ notice: "Nenhuma IA selecionada." });

    expect(screen.getByRole("status")).toHaveTextContent("Nenhuma IA selecionada.");
  });
});

describe("composer — seletor de IA", () => {
  it("mostra 'Selecionar IA' quando o provider ativo não é oferecível", () => {
    renderComposer({ provider: "local_qa", providerIsSelectable: false });

    expect(screen.getByLabelText("IA utilizada nesta conversa")).toHaveValue("");
  });

  it("oferece apenas os providers recebidos do pai", () => {
    renderComposer();

    const options = screen.getAllByRole("option").map((item) => item.textContent);

    expect(options).toEqual(["Selecionar IA", "Gemini"]);
  });

  it("lista IA pública indisponível, desabilitada e com o motivo no rótulo", () => {
    renderComposer({ offeredProviders: [GEMINI, OPENAI] });

    const openai = screen.getByRole("option", { name: "OpenAI — não configurado" });

    expect(openai).toBeInTheDocument();
    expect(openai).toBeDisabled();
  });

  it("mantém a IA configurada e homologada habilitada no dropdown", () => {
    renderComposer({ offeredProviders: [GEMINI, OPENAI] });

    expect(screen.getByRole("option", { name: "Gemini" })).toBeEnabled();
  });

  it("não exibe badge DEV para uma IA pública", () => {
    renderComposer();

    expect(screen.queryByText("DEV")).toBeNull();
  });

  it("marca visivelmente o provider interno como ambiente técnico", () => {
    renderComposer({
      offeredProviders: [GEMINI, MOCK],
      provider: "mock",
      providerIsDev: true,
    });

    expect(screen.getByText("DEV")).toBeInTheDocument();
  });

  it("agrupa o seletor de IA junto do botão Enviar, à direita da barra", () => {
    const { container } = render(
      <ChatComposer
        value=""
        loading={false}
        placeholder="Digite sua mensagem..."
        offeredProviders={[GEMINI]}
        provider="gemini"
        providerIsSelectable
        providerIsDev={false}
        notice=""
        canSend
        attachments={[]}
        onChange={vi.fn()}
        onProviderChange={vi.fn()}
        onSend={vi.fn()}
        onAttachmentsSelected={vi.fn()}
        onAttachmentRemove={vi.fn()}
      />,
    );

    const group = container.querySelector(".composer-send-group");

    expect(group).not.toBeNull();
    // Seletor e Enviar no MESMO contêiner, nessa ordem; anexo e microfone ficam
    // no grupo da esquerda.
    expect(group?.querySelector("#composer-provider")).not.toBeNull();
    expect(group?.querySelector(".send-button")).not.toBeNull();
    expect(group?.querySelector(".composer-icon-button")).toBeNull();
  });
});

describe("composer — anexos", () => {
  it("lista nome, tamanho e tipo do anexo", () => {
    renderComposer({
      attachments: [
        { id: "1", name: "dados.csv", size: 8192, artifactType: "text", content: "a,b" },
      ],
    });

    expect(screen.getByText("dados.csv")).toBeInTheDocument();
    expect(screen.getByText("8.0 KB")).toBeInTheDocument();
    expect(screen.getByText("text")).toBeInTheDocument();
  });

  it("nunca mostra o conteúdo do arquivo na tela", () => {
    renderComposer({
      attachments: [
        { id: "1", name: "segredo.txt", size: 20, artifactType: "text", content: "CONTEUDO-SIGILOSO" },
      ],
    });

    expect(screen.queryByText("CONTEUDO-SIGILOSO")).toBeNull();
  });

  it("remove um anexo pelo botão correspondente", () => {
    const props = renderComposer({
      attachments: [
        { id: "abc", name: "notas.md", size: 10, artifactType: "markdown", content: "#" },
      ],
    });

    fireEvent.click(screen.getByRole("button", { name: "Remover anexo notas.md" }));

    expect(props.onAttachmentRemove).toHaveBeenCalledWith("abc");
  });

  it("entrega os arquivos escolhidos ao pai", () => {
    // O spy é criado aqui, e não lido do objeto de props, porque o spread de
    // `renderComposer` alarga o tipo e esconde a API de mock.
    const onAttachmentsSelected = vi.fn();
    renderComposer({ onAttachmentsSelected });

    fireEvent.change(document.getElementById("composer-attachment-input") as HTMLInputElement, {
      target: { files: [new File(["# t"], "notas.md", { type: "text/markdown" })] },
    });

    expect(onAttachmentsSelected).toHaveBeenCalledTimes(1);
    expect(onAttachmentsSelected.mock.calls[0][0][0].name).toBe("notas.md");
  });

  it("desabilita o botão de anexar ao atingir o limite", () => {
    renderComposer({
      attachments: Array.from({ length: 4 }, (_, index) => ({
        id: `${index}`,
        name: `a${index}.txt`,
        size: 10,
        artifactType: "text",
        content: "x",
      })),
    });

    expect(screen.getByRole("button", { name: /Limite de 4 anexos/ })).toBeDisabled();
  });
});

describe("composer — microfone", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("desabilita o botão e explica quando o navegador não suporta", () => {
    vi.stubGlobal("SpeechRecognition", undefined);
    vi.stubGlobal("webkitSpeechRecognition", undefined);

    renderComposer();

    const button = screen.getByRole("button", {
      name: "Ditado por voz indisponível neste navegador",
    });

    expect(button).toBeDisabled();
  });

  it("reconhece o construtor prefixado do Chromium", () => {
    vi.stubGlobal("SpeechRecognition", undefined);
    stubSpeechRecognition("webkitSpeechRecognition");

    renderComposer();

    expect(screen.getByRole("button", { name: "Ditar mensagem por voz" })).toBeEnabled();
  });

  it("inicia a escuta em pt-BR e sinaliza o estado", () => {
    const instance = stubSpeechRecognition();

    renderComposer();
    fireEvent.click(screen.getByRole("button", { name: "Ditar mensagem por voz" }));

    expect(instance.start).toHaveBeenCalledTimes(1);
    expect(instance.lang).toBe("pt-BR");
    expect(screen.getByRole("button", { name: "Parar ditado e manter o texto" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("entrega a transcrição final ao textarea, sem enviar automaticamente", () => {
    const instance = stubSpeechRecognition();
    const props = renderComposer({ value: "início" });

    fireEvent.click(screen.getByRole("button", { name: "Ditar mensagem por voz" }));

    act(() =>
      instance.onresult?.({
        resultIndex: 0,
        results: [Object.assign([{ transcript: "olá mundo" }], { isFinal: true })],
      }),
    );

    expect(props.onChange).toHaveBeenCalledWith("início olá mundo");
    expect(props.onSend).not.toHaveBeenCalled();
  });

  it("ignora resultado ainda não final", () => {
    const instance = stubSpeechRecognition();
    const props = renderComposer();

    fireEvent.click(screen.getByRole("button", { name: "Ditar mensagem por voz" }));

    act(() =>
      instance.onresult?.({
        resultIndex: 0,
        results: [Object.assign([{ transcript: "parcial" }], { isFinal: false })],
      }),
    );

    expect(props.onChange).not.toHaveBeenCalled();
  });

  it("informa permissão negada", () => {
    const instance = stubSpeechRecognition();

    renderComposer();
    fireEvent.click(screen.getByRole("button", { name: "Ditar mensagem por voz" }));
    // O callback vem do navegador, fora do React: `act` garante que a
    // atualização de estado seja aplicada antes da consulta.
    act(() => instance.onerror?.({ error: "not-allowed" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Permissão de microfone negada");
  });

  it("informa erro genérico de transcrição", () => {
    const instance = stubSpeechRecognition();

    renderComposer();
    fireEvent.click(screen.getByRole("button", { name: "Ditar mensagem por voz" }));
    act(() => instance.onerror?.({ error: "network" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Falha de rede");
  });

  it("cancelar aborta o reconhecimento sem apresentar erro ao usuário", () => {
    const instance = stubSpeechRecognition();

    renderComposer();
    fireEvent.click(screen.getByRole("button", { name: "Ditar mensagem por voz" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancelar ditado e descartar" }));

    expect(instance.abort).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("parar encerra mantendo o texto já transcrito", () => {
    const instance = stubSpeechRecognition();

    renderComposer();
    fireEvent.click(screen.getByRole("button", { name: "Ditar mensagem por voz" }));
    fireEvent.click(screen.getByRole("button", { name: "Parar ditado e manter o texto" }));

    expect(instance.stop).toHaveBeenCalledTimes(1);
    expect(instance.abort).not.toHaveBeenCalled();
  });
});
